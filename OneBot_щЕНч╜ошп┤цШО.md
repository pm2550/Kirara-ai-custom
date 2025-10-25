# OneBot 第三方 QQ 协议配置说明

## 📋 概述

Kirara AI 通过 HTTP Legacy 适配器支持 OneBot 第三方 QQ 协议。这意味着您可以使用任何支持 OneBot 协议的 QQ 机器人框架，如：

- **go-cqhttp** (推荐)
- **mirai**
- **Shamrock**
- **其他 OneBot 兼容框架**

## 🔧 配置步骤

### 1. 下载并配置 go-cqhttp

1. 访问 [go-cqhttp 发布页面](https://github.com/Mrs4s/go-cqhttp/releases)
2. 下载适合您系统的版本
3. 解压到任意目录

### 2. 配置 go-cqhttp

创建 `config.yml` 文件：

```yaml
# go-cqhttp 配置文件
account:
  uin: 你的QQ号
  password: '你的QQ密码'  # 或使用二维码登录
  encrypt: false
  status: 0
  relogin:
    delay: 3
    interval: 3
    max-times: 0
  use-sso-address: true

heartbeat:
  interval: 5

message:
  post-format: string
  ignore-invalid-cqcode: false
  force-fragment: false
  fix-url: false
  proxy-rewrite: ''
  report-self-message: false
  remove-reply-at: false
  extra-reply-data: false
  skip-mime-scan: false

output:
  log-level: info
  log-aging: 15
  log-force-new: true
  log-colorful: true
  debug: false

default-middlewares: &default
  access-token: ''
  filter: ''
  rate-limit:
    enabled: false
    frequency: 1
    bucket: 1

servers:
  # HTTP 通信设置
  - http:
      address: 0.0.0.0:5700
      timeout: 5
      long-polling:
        enabled: false
        max-queue-size: 2000
      middlewares:
        <<: *default
      post:
        - url: 'http://127.0.0.1:8080/v1/chat'  # Kirara AI 的 HTTP API 地址
          secret: ''  # 如果 Kirara AI 设置了 api_key，这里也要设置相同的值
```

### 3. 启动 go-cqhttp

```bash
# Windows
go-cqhttp.exe

# Linux/Mac
./go-cqhttp
```

首次运行会要求登录，可以选择：
- 密码登录
- 二维码登录（推荐）

### 4. 配置 Kirara AI

确保 `config.yaml` 中的配置正确：

```yaml
ims:
  - name: "onebot-http-adapter"
    enable: true
    adapter: "http_legacy"
    config:
      api_key: "your-secret-key"  # 设置一个安全的密钥
```

## 🔗 API 接口说明

Kirara AI 提供以下 HTTP API 接口供 OneBot 调用：

### POST /v1/chat

**请求参数：**
```json
{
    "session_id": "group-群号:用户QQ号",  // 群聊格式
    "username": "用户昵称",
    "message": "用户消息内容"
}
```

**响应格式：**
```json
{
    "result": "DONE",
    "message": ["机器人回复"],
    "voice": [],
    "image": []
}
```

### POST /v2/chat (异步版本)

**请求参数：**
```json
{
    "session_id": "group-群号:用户QQ号",
    "username": "用户昵称", 
    "message": "用户消息内容"
}
```

**响应：** 返回 request_id

### GET /v2/chat/response

**请求参数：**
- `request_id`: v2/chat 返回的请求ID

**响应格式：**
```json
{
    "result": "DONE",
    "message": ["机器人回复"],
    "voice": [],
    "image": []
}
```

## 🚀 启动 Kirara AI

```bash
cd kirara-ai
python -m kirara_ai
```

## 🔍 测试连接

1. 启动 Kirara AI
2. 启动 go-cqhttp
3. 在 QQ 群或私聊中发送消息
4. 检查 Kirara AI 控制台是否有日志输出

## ⚠️ 注意事项

1. **API 密钥安全**：建议设置 `api_key` 以确保安全
2. **端口配置**：确保 go-cqhttp 和 Kirara AI 的端口不冲突
3. **防火墙**：确保相关端口在防火墙中开放
4. **QQ 账号安全**：使用小号进行测试，避免主号被封

## 🛠️ 故障排除

### 常见问题

1. **连接失败**
   - 检查端口是否正确
   - 检查防火墙设置
   - 检查 API 密钥是否匹配

2. **消息无响应**
   - 检查 go-cqhttp 日志
   - 检查 Kirara AI 日志
   - 确认 LLM 配置正确

3. **登录失败**
   - 尝试二维码登录
   - 检查 QQ 账号状态
   - 更新 go-cqhttp 版本

## 📚 更多资源

- [go-cqhttp 官方文档](https://docs.go-cqhttp.org/)
- [OneBot 协议规范](https://onebot.dev/)
- [Kirara AI 官方文档](https://kirara-docs.app.lss233.com/)

