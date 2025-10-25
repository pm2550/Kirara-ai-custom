# Kirara AI - Custom Configuration

This is my custom configuration for Kirara AI.

## About

This repository contains my personal setup and configurations for the Kirara AI chatbot.

**Original Project:** [lss233/kirara-ai](https://github.com/lss233/kirara-ai)

## Usage

Refer to the [official documentation](https://kirara-docs.app.lss233.com/) for setup and usage instructions.

## 📷 功能展示

| ![猫娘问答](https://img.shields.io/badge/-%E7%8C%AB%E5%A8%98%E9%97%AE%E7%AD%94-FF6B6B?style=for-the-badge&logo=github&logoColor=white) | ![智能助手](https://img.shields.io/badge/-智能助手-4ECDC4?style=for-the-badge&logo=wechat&logoColor=white) | ![沉浸式RPG](https://img.shields.io/badge/-沉浸式RPG-FFA07A?style=for-the-badge&logo=discord&logoColor=white) |
|:-------------------------------:|:-------------------------------:|:-------------------------------:|
| ![猫娘模式](https://user-images.githubusercontent.com/8984680/230702158-73967aa9-01be-44d6-bbd9-24437e333140.png) | ![日常助手](https://user-images.githubusercontent.com/8984680/230702177-de96f89b-053e-4313-a131-715af969db04.png) | ![文字冒险](https://user-images.githubusercontent.com/8984680/230702635-fb1de3bf-acbd-46ca-8d6f-caa47368b4d4.png) |

## 🧭 WebUI  

<div align="center">  

<h3 align="center">模型管理</h3>  

![image](https://github.com/user-attachments/assets/0839bff6-47d4-4fe2-a326-056185ef1ad4)


<h3 align="center">工作流</h3>  

![image](https://github.com/user-attachments/assets/c8ded878-3cf9-4c70-925d-ee29027674ff)

<h3 align="center">插件市场</h3>  

![image](https://github.com/user-attachments/assets/d734be88-e8f6-4b95-aba8-02a544ab7a9f)

</div>

## ⚡ 核心特性
* [x] 图片发送
* [x] 关键词触发回复
* [x] 多账号支持
* [x] 人格设定
* [x] 支持 QQ、Telegram、Discord、微信  
* [x] 可作为 HTTP 服务端提供 Web API
* [x] 支持 OpenAI、DeepSeek、Claude、Gemini、Qwen、Mistral、豆包、Minimax、Kimi、Mistral 等主流大模型
* [x] 支持插件机制
* [x] 支持条件触发
* [x] 支持管理员指令
* [x] 支持 Stable Diffusion、Flux、Midjourney 等绘图模型
* [x] 支持语音回复
* [x] 支持多轮对话
* [x] 支持跨平台消息发送
* [x] 支持自定义工作流
* [x] 支持 Web 管理后台
* [x] 内置 Frpc 内网穿透

# **🤖 聊天平台**  

我们支持多种聊天平台。  

| 平台       | 群聊回复 | 私聊回复 | 条件触发 | 管理员指令 | 绘图  | 语音回复 |
|----------|------|------|------|-------|-----|------|
| Telegram | 支持   | 支持   | 支持 | 支持  | 支持  | 支持   |
| QQ 机器人 | 支持   | 支持   | 支持 | 支持  | 支持  | 平台不支持   |
| Discord  | 重构中   | 重构中   | 重构中 | 重构中  | 重构中  | 重构中   |
| 飞书机器人  | 重构中   | 重构中   | 重构中 | 重构中  | 重构中  | 重构中   |
| 企业微信应用 | 支持   | 支持   | 支持 | 不支持  | 支持  | 支持   |
| 微信公众号 | 支持   | 支持   | 支持 | 不支持  | 支持  | 支持   |
| OneBot   | 插件支持   | 插件支持   | 插件支持   | 插件支持    | 插件支持  | 插件支持   |

## 🐎 命令

**你可以在 WebUI 的调度规则中自定义所有命令。**  


## 🔧 搭建

请移步至 [快速开始](https://kirara-docs.app.lss233.com/guide/getting-started.html)

## 🕸 HTTP API

<details>
    <summary>HTTP API 可用于接入其他平台。</summary>
在聊天平台管理中启动 http-legacy 适配器后，将提供以下接口：  

**POST**    `/v1/chat`  

**请求参数**  

|参数名|必选|类型|说明|
|:---|:---|:---|:---|
|session_id| 是 | String |会话ID，默认：`friend-default_session`|
|username| 是 | String |用户名，默认：`某人`|
|message| 是 | String |消息，不能为空|  

**请求示例**
```json
{
    "session_id": "friend-123456",
    "username": "testuser",
    "message": "ping"
}
```
**响应格式**
|参数名|类型|说明|
|:---|:---|:---|
|result| String |SUCESS,DONE,FAILED|
|message| String[] |文本返回，支持多段返回|
|voice| String[] |音频返回，支持多个音频的base64编码；参考：data:audio/mpeg;base64,...|
|image| String[] |图片返回，支持多个图片的base64编码；参考：data:image/png;base64,...|

**响应示例**  
```json
{
    "result": "DONE",
    "message": ["pong!"],
    "voice": [],
    "image": []
}
```

**POST**    `/v2/chat`  

**请求参数**  

|参数名|必选|类型|说明|
|:---|:---|:---|:---|
|session_id| 是 | String |会话ID，默认：`friend-default_session`|
|username| 是 | String |用户名，默认：`某人`|
|message| 是 | String |消息，不能为空|  

**请求示例**
```json
{
    "session_id": "friend-123456",
    "username": "testuser",
    "message": "ping"
}
```
**响应格式**
字符串：request_id

**响应示例**  
```
1681525479905
```

**GET**    `/v2/chat/response`  

**请求参数**  

|参数名|必选|类型|说明|
|:---|:---|:---|:---|
|request_id| 是 | String |请求id，/v2/chat返回的值|

**请求示例**
```
/v2/chat/response?request_id=1681525479905
```
**响应格式**
|参数名|类型|说明|
|:---|:---|:---|
|result| String |SUCESS,DONE,FAILED|
|message| String[] |文本返回，支持多段返回|
|voice| String[] |音频返回，支持多个音频的base64编码；参考：data:audio/mpeg;base64,...|
|image| String[] |图片返回，支持多个图片的base64编码；参考：data:image/png;base64,...|

* 每次请求返回增量并清空。DONE、FAILED之后没有更多返回。

**响应示例**  
```json
{
    "result": "DONE",
    "message": ["pong!"],
    "voice": ["data:audio/mpeg;base64,..."],
    "image": ["data:image/png;base64,...", "data:image/png;base64,..."]
}
```
</details>

## 🦊 加载预设

如果你想让机器人自动带上某种聊天风格，可以使用预设功能。  

我们自带了 `猫娘` 和 `正常` 两种预设，你可以在 `presets` 文件夹下了解预设的写法。  

使用 `加载预设 猫娘` 来加载猫娘预设。

下面是一些预设的小视频，你可以看看效果：
* MOSS： https://www.bilibili.com/video/av352047018
* 丁真：https://www.bilibili.com/video/av267013053
* 小黑子：https://www.bilibili.com/video/av309604568
* 高启强：https://www.bilibili.com/video/av779555493

关于预设系统的详细教程：[Wiki](https://github.com/lss233/kirara-ai/wiki/%F0%9F%90%B1-%E9%A2%84%E8%AE%BE%E7%B3%BB%E7%BB%9F)

你可以在 [Awesome ChatGPT QQ Presets](https://github.com/lss233/awesome-chatgpt-qq-presets/tree/master) 获取由大家分享的预设。

你也可以参考 [Awesome-ChatGPT-prompts-ZH_CN](https://github.com/L1Xu4n/Awesome-ChatGPT-prompts-ZH_CN) 来调教你的 ChatGPT，还可以参考 [Awesome ChatGPT Prompts](https://github.com/f/awesome-chatgpt-prompts) 来解锁更多技能。 

## 🎙 文字转语音

自 v2.2.5 开始，我们支持接入微软的 Azure 引擎 和 VITS 引擎，让你的机器人发送语音。

**提示**：在 Windows 平台上使用语音功能需要安装最新的 VC 运行库，你可以在[这里](https://learn.microsoft.com/zh-CN/cpp/windows/latest-supported-vc-redist?view=msvc-170)下载。`

## 🛠 贡献者名单   

欢迎提出新的点子、 Pull Request。  

<a href="https://github.com/lss233/kirara-ai/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=lss233/kirara-ai" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## 📕 相关项目

- [Kirara Registry](https://github.com/DarkSkyTeam/kirara-registry) - Kirara AI 插件市场
- [Kirara WebUI](https://github.com/DarkSkyTeam/kirara-webui) - Kirara AI 的 WebUI 前端项目
- [Kirara Docs](https://github.com/DarkSkyTeam/kirara-docs) - Kirara AI 的使用手册原始文档

## 💪 支持我们

如果我们这个项目对你有所帮助，请给我们一颗 ⭐️  

[![Star History Chart](https://api.star-history.com/svg?repos=lss233/kirara-ai&type=Date)](https://www.star-history.com/#lss233/kirara-ai&Date)
