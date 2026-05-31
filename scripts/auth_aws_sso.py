#!/usr/bin/env python3
"""
Trae AI AWS SSO 企业认证脚本

实现完整的 AWS SSO OIDC → GetRoleCredentials → STS AssumeRole 认证链。
用于 AWS Bedrock 运行时认证。

用法:
    python scripts/auth_aws_sso.py --action register-client
    python scripts/auth_aws_sso.py --action sso-login --start-url <url> --client-id <id>
    python scripts/auth_aws_sso.py --action get-credentials --access-token <token> --account-id <id> --role-name <role>
    python scripts/auth_aws_sso.py --action bedrock-test --region us-east-1
"""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

import requests


def sso_oidc_register_client(region: str = "us-east-1") -> Dict[str, Any]:
    """注册 OIDC 客户端。POST https://oidc.{region}.amazonaws.com/client/register"""
    url = f"https://oidc.{region}.amazonaws.com/client/register"
    payload = {"clientName": "trae-ai-client", "clientType": "public", "scopes": ["openid", "profile"]}
    print(f"[*] 注册 OIDC 客户端: {url}")
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code == 200:
        result = resp.json()
        print(f"[+] 注册成功: clientId={result.get('clientId', 'N/A')}")
        return result
    print(f"[!] 注册失败 ({resp.status_code})，可能已存在")
    return {"clientId": "", "clientSecret": ""}


def sso_oidc_start_device_auth(client_id: str, client_secret: str = "",
                                start_url: str = "", region: str = "us-east-1") -> Dict[str, Any]:
    """启动设备授权。POST https://oidc.{region}.amazonaws.com/device_authorization"""
    url = f"https://oidc.{region}.amazonaws.com/device_authorization"
    payload = {"clientId": client_id, "startUrl": start_url}
    if client_secret:
        payload["clientSecret"] = client_secret
    print(f"[*] 启动设备授权: {url}")
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    print(f"\n[!] 浏览器打开: {result.get('verificationUriComplete', 'N/A')}")
    print(f"    设备码: {result.get('userCode', 'N/A')}")
    print(f"    有效期: {result.get('expiresIn', 0)} 秒\n")
    return result


def sso_oidc_create_token(client_id: str, client_secret: str, device_code: str,
                           region: str = "us-east-1") -> Dict[str, Any]:
    """轮询设备授权结果。POST https://oidc.{region}.amazonaws.com/token"""
    url = f"https://oidc.{region}.amazonaws.com/token"
    payload = {
        "clientId": client_id, "clientSecret": client_secret,
        "grantType": "urn:ietf:params:oauth:grant-type:device_code", "deviceCode": device_code,
    }
    for attempt in range(60):
        print(f"[*] 轮询 ({attempt + 1}/60)...")
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            print(f"[+] Token 获取成功: {result.get('accessToken', 'N/A')[:30]}...")
            return result
        if resp.status_code == 400:
            err = resp.json().get("error", "")
            if err == "AuthorizationPendingException":
                time.sleep(5); continue
            if err == "SlowDownException":
                time.sleep(10); continue
            if err == "ExpiredTokenException":
                print("[!] 设备码已过期"); return {"error": "token_expired"}
        print(f"[!] 错误: {resp.status_code} {resp.text[:100]}")
        time.sleep(5)
    print("[!] 轮询超时")
    return {"error": "timeout"}


def sso_get_role_credentials(access_token: str, account_id: str, role_name: str,
                              region: str = "us-east-1") -> Dict[str, Any]:
    """获取角色凭证。POST https://portal.sso.{region}.amazonaws.com/federation/credentials"""
    url = f"https://portal.sso.{region}.amazonaws.com/federation/credentials"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"accountId": account_id, "roleName": role_name}
    print(f"[*] 获取角色凭证: account={account_id} role={role_name}")
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    print(f"[+] 成功: accessKeyId={result.get('accessKeyId', 'N/A')[:10]}...")
    return result


def sts_assume_role(access_key: str, secret_key: str, session_token: str,
                    role_arn: str, session_name: str = "trae-session",
                    region: str = "us-east-1") -> Dict[str, Any]:
    """STS AssumeRole。"""
    url = f"https://sts.{region}.amazonaws.com/"
    payload = {"Action": "AssumeRole", "RoleArn": role_arn,
               "RoleSessionName": session_name, "Version": "2011-06-15"}
    print(f"[*] STS AssumeRole: {role_arn}")
    resp = requests.post(url, data=payload, timeout=10)
    if resp.status_code == 200:
        root = ET.fromstring(resp.text)
        ns = {"sts": "https://sts.amazonaws.com/doc/2011-06-15/"}
        creds = root.find(".//sts:Credentials", ns)
        if creds is not None:
            return {
                "access_key_id": creds.find("sts:AccessKeyId", ns).text,
                "secret_access_key": creds.find("sts:SecretAccessKey", ns).text,
                "session_token": creds.find("sts:SessionToken", ns).text,
                "expiration": creds.find("sts:Expiration", ns).text,
            }
    print(f"[!] AssumeRole 失败: {resp.status_code}")
    return {"error": "assume_role_failed"}


def bedrock_test_connection(access_key: str, secret_key: str, session_token: str,
                             region: str = "us-east-1",
                             model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0") -> bool:
    """测试 Bedrock Converse Stream 连接。"""
    url = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke-with-response-stream"
    payload = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 100,
               "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]}
    try:
        print(f"[*] 测试 Bedrock: {model_id} @ {region}")
        resp = requests.post(url, json=payload, timeout=30)
        print(f"[{'✓' if resp.status_code == 200 else '✗'}] Bedrock: {resp.status_code}")
        return resp.status_code == 200
    except requests.RequestException as e:
        print(f"[✗] 连接失败: {e}")
        return False


def parse_args():
    parser = argparse.ArgumentParser(description="AWS SSO 企业认证")
    parser.add_argument("--action", required=True, choices=[
        "register-client", "sso-login", "get-credentials", "assume-role", "bedrock-test",
    ])
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--start-url")
    parser.add_argument("--device-code")
    parser.add_argument("--access-token")
    parser.add_argument("--account-id")
    parser.add_argument("--role-name")
    parser.add_argument("--role-arn")
    parser.add_argument("--session-name", default="trae-session")
    parser.add_argument("--model-id", default="anthropic.claude-3-sonnet-20240229-v1:0")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.action == "register-client":
        result = sso_oidc_register_client(args.region)
        print(json.dumps(result, indent=2))

    elif args.action == "sso-login":
        if not args.start_url or not args.client_id:
            print("[!] 需要 --start-url --client-id"); sys.exit(1)
        result = sso_oidc_start_device_auth(args.client_id, args.client_secret or "", args.start_url, args.region)
        print(json.dumps(result, indent=2))

    elif args.action == "get-credentials":
        if not all([args.access_token, args.account_id, args.role_name]):
            print("[!] 需要 --access-token --account-id --role-name"); sys.exit(1)
        result = sso_get_role_credentials(args.access_token, args.account_id, args.role_name, args.region)
        print(json.dumps(result, indent=2))

    elif args.action == "assume-role":
        if not args.role_arn:
            print("[!] 需要 --role-arn"); sys.exit(1)
        ak = os.environ.get("AWS_ACCESS_KEY_ID")
        sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
        st = os.environ.get("AWS_SESSION_TOKEN")
        if not all([ak, sk, st]):
            print("[!] 需要设置 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN"); sys.exit(1)
        result = sts_assume_role(ak, sk, st, args.role_arn, args.session_name, args.region)
        print(json.dumps(result, indent=2))

    elif args.action == "bedrock-test":
        ak = os.environ.get("AWS_ACCESS_KEY_ID")
        sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
        st = os.environ.get("AWS_SESSION_TOKEN")
        if not all([ak, sk, st]):
            print("[!] 需要设置 AWS 凭证环境变量"); sys.exit(1)
        bedrock_test_connection(ak, sk, st, args.region, args.model_id)


if __name__ == "__main__":
    main()
