import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/trae-reverse-engineering/',
  title: 'trae ide逆向分析',
  description: 'trae ide逆向分析',
  lang: 'zh-CN',
  lastUpdated: true,
  ignoreDeadLinks: true,
  markdown: {
    lineNumbers: true,
  },
  themeConfig: {
    search: {
      provider: 'local',
    },
    nav: [
      { text: '文档首页', link: '/' },
      { text: 'GitHub', link: 'https://github.com/vibe-coding-labs/trae-reverse-engineering' },
    ],
    sidebar: [
          { text: "trae ide逆向分析", items: [
            { text: "首页", link: "/" },
            { text: "Trae AI Proxy Implementation Summary", link: "/proxy-implementation-summary" },
            { text: "Trae AI Proxy - Quick Reference Card", link: "/proxy-quick-reference" },
            { text: "Trae Multi-Platform Download & Reverse Engineering Plan", link: "/superpowers/plans/2026-05-27-trae-download-and-reverse-engineering" },
            { text: "Trae AI Communication Protocol Reverse Engineering Plan", link: "/superpowers/plans/2026-05-28-trae-ai-protocol-reverse-engineering" },
            { text: "认证授权协议完整分析与脚本编写计划", link: "/superpowers/plans/2026-05-31-auth-protocol-scripts" },
            { text: "Protocol Analysis Continuation Plan", link: "/superpowers/plans/2026-05-31-protocol-analysis-continuation" },
            { text: "Trae IDE 全面逆向分析 — 持续调研与执行计划", link: "/superpowers/plans/2026-06-01-trae-full-reverse-engineering-plan" },
            { text: "Trae AI API 账号 & 配额问题解决方案报告", link: "/superpowers/plans/2026-06-03-account-quota-solution" },
            { text: "Trae AI 账号注册 & 配额自动化方案", link: "/superpowers/plans/2026-06-03-token-procurement-plan" },
          ] }
        ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/vibe-coding-labs/trae-reverse-engineering' },
    ],
    footer: {
      message: '基于 VitePress 构建',
    },
  },
})
