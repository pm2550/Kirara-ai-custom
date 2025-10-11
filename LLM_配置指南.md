# 大语言模型配置指南

## 🎯 支持的模型

Kirara AI 支持多种主流大语言模型：

- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **DeepSeek** (deepseek-chat, deepseek-coder)
- **Claude** (Anthropic)
- **Gemini** (Google)
- **Qwen** (阿里云)
- **Mistral**
- **豆包** (字节跳动)
- **Minimax**
- **Kimi** (月之暗面)
- **Ollama** (本地部署)

## 🔧 配置方法

### 1. OpenAI 配置

```yaml
llms:
  api_backends:
    - name: "openai-gpt4"
      adapter: "openai"
      enable: true
      config:
        api_key: "sk-your-openai-api-key"
        api_base: "https://api.openai.com/v1"
      models:
        - "gpt-4"
        - "gpt-4-turbo"
        - "gpt-3.5-turbo"
```

### 2. DeepSeek 配置

```yaml
llms:
  api_backends:
    - name: "deepseek-official"
      adapter: "deepseek"
      enable: true
      config:
        api_key: "sk-your-deepseek-api-key"
        api_base: "https://api.deepseek.com/v1"
      models:
        - "deepseek-chat"
        - "deepseek-coder"
```

### 3. Claude 配置

```yaml
llms:
  api_backends:
    - name: "claude-official"
      adapter: "claude"
      enable: true
      config:
        api_key: "your-claude-api-key"
        api_base: "https://api.anthropic.com"
      models:
        - "claude-3-5-sonnet-20241022"
        - "claude-3-5-haiku-20241022"
```

### 4. Gemini 配置

```yaml
llms:
  api_backends:
    - name: "gemini-official"
      adapter: "gemini"
      enable: true
      config:
        api_key: "your-gemini-api-key"
        api_base: "https://generativelanguage.googleapis.com/v1beta"
      models:
        - "gemini-1.5-flash"
        - "gemini-1.5-pro"
```

### 5. Ollama 本地配置

```yaml
llms:
  api_backends:
    - name: "ollama-local"
      adapter: "ollama"
      enable: true
      config:
        api_base: "http://localhost:11434"
      models:
        - "llama3.2"
        - "qwen2.5"
        - "deepseek-coder"
```

## 🔑 获取 API Key

### OpenAI
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API Key

### DeepSeek
1. 访问 [DeepSeek Platform](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入 API 管理页面
4. 创建新的 API Key

### Claude
1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API Key

### Gemini
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用 Google 账号登录
3. 创建新的 API Key

## 🚀 快速开始

### 方法一：使用免费模型

推荐使用 **DeepSeek** 或 **Gemini**，它们提供免费额度：

1. 获取 API Key
2. 在 `config.yaml` 中配置对应模型
3. 将 `enable` 设置为 `true`
4. 设置 `defaults.llm_model` 为对应模型名

### 方法二：使用本地模型

使用 **Ollama** 在本地部署模型：

1. 安装 Ollama：
   ```bash
   # Windows
   # 下载安装包：https://ollama.ai/download
   
   # Linux/Mac
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. 下载模型：
   ```bash
   ollama pull llama3.2
   ollama pull qwen2.5
   ```

3. 配置 Kirara AI：
   ```yaml
   llms:
     api_backends:
       - name: "ollama-local"
         adapter: "ollama"
         enable: true
         config:
           api_base: "http://localhost:11434"
         models:
           - "llama3.2"
   
   defaults:
     llm_model: "llama3.2"
   ```

## ⚙️ 高级配置

### 多模型配置

```yaml
llms:
  api_backends:
    - name: "openai-gpt4"
      adapter: "openai"
      enable: true
      config:
        api_key: "sk-your-openai-key"
        api_base: "https://api.openai.com/v1"
      models:
        - "gpt-4"
        - "gpt-4-turbo"
    
    - name: "deepseek-official"
      adapter: "deepseek"
      enable: true
      config:
        api_key: "sk-your-deepseek-key"
        api_base: "https://api.deepseek.com/v1"
      models:
        - "deepseek-chat"
        - "deepseek-coder"

defaults:
  llm_model: "gpt-4"  # 默认使用 GPT-4
```

### 代理配置

如果需要使用代理：

```yaml
llms:
  api_backends:
    - name: "openai-gpt4"
      adapter: "openai"
      enable: true
      config:
        api_key: "sk-your-openai-key"
        api_base: "https://api.openai.com/v1"
        proxy: "http://127.0.0.1:7890"  # 代理地址
      models:
        - "gpt-4"
```

## 🔍 测试配置

启动 Kirara AI 后，可以通过以下方式测试：

1. **Web 界面测试**：
   - 访问 `http://127.0.0.1:8080`
   - 在聊天界面发送消息测试

2. **API 测试**：
   ```bash
   curl -X POST "http://127.0.0.1:8080/v1/chat" \
        -H "Content-Type: application/json" \
        -d '{
          "session_id": "test-session",
          "username": "testuser",
          "message": "你好"
        }'
   ```

## ⚠️ 注意事项

1. **API Key 安全**：不要将 API Key 提交到版本控制系统
2. **费用控制**：注意 API 调用费用，设置合理的限制
3. **网络连接**：确保网络可以访问对应的 API 服务
4. **模型可用性**：某些模型可能有地域限制

## 🛠️ 故障排除

### 常见问题

1. **API Key 无效**
   - 检查 API Key 是否正确
   - 确认账号是否有足够余额
   - 检查 API Key 权限

2. **网络连接失败**
   - 检查网络连接
   - 尝试使用代理
   - 检查防火墙设置

3. **模型不可用**
   - 检查模型名称是否正确
   - 确认模型是否在支持列表中
   - 检查 API 服务状态

## 📚 更多资源

- [OpenAI API 文档](https://platform.openai.com/docs)
- [DeepSeek API 文档](https://platform.deepseek.com/api-docs/)
- [Ollama 官方文档](https://ollama.ai/docs)
- [Kirara AI 官方文档](https://kirara-docs.app.lss233.com/)

