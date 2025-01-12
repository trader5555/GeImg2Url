Here is the README.md with setup instructions:

```markdown
# GeImg2Url Plugin

专门为gewechat通道设计的图片转链接插件。

## 配置说明
1. 在config.json中配置imgbb_api_key
2. 确保channel_type设置为"gewechat"
3. 需要正确配置以下gewechat参数:
   - gewechat_base_url
   - gewechat_token
   - gewechat_app_id
   - gewechat_download_url

## 使用方法
1. 发送"图转链接"触发插件
2. 收到提示后发送图片
3. 插件会返回可访问的图片URL

## 注意事项
- 本插件仅支持gewechat通道使用
- 需要正确配置imgbb_api_key才能使用
- 使用前请确保所有gewechat配置参数正确
```

Save this file as `plugins/GeImg2Url/README.md` in your dify-on-wechat installation.
