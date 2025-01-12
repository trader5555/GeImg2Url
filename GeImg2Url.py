import os
import json
import requests
import base64
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins import EventAction, Plugin, register
from common.log import logger
from config import conf

@register(
    name="GeImg2Url",
    desire_priority=200,
    hidden=False,
    desc="图片转链接插件 (仅支持gewechat通道)",
    version="1.0",
    author="微信atrader",
)
class GeImg2Url(Plugin):
    def __init__(self):
        super().__init__()
        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self.imgbb_api_key = None
        self.trigger_word = "图转链接"
        self.waiting_for_image = {}
        
        # 加载配置
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.imgbb_api_key = config.get("imgbb_api_key", "")
        except Exception as e:
            logger.error(f"[GeImg2Url] 配置文件加载失败: {e}")

        # 验证配置
        self._validate_config()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

    def _validate_config(self):
        """验证必要的配置"""
        if not self.imgbb_api_key:
            logger.error("[GeImg2Url] 请在plugins/GeImg2Url/config.json中配置imgbb_api_key")
            
        required_configs = {
            'gewechat_base_url': conf().get('gewechat_base_url'),
            'gewechat_app_id': conf().get('gewechat_app_id'),
            'gewechat_token': conf().get('gewechat_token'),
            'gewechat_download_url': conf().get('gewechat_download_url')
        }
        
        missing_configs = [k for k, v in required_configs.items() if not v]
        if missing_configs:
            logger.error(f"[GeImg2Url] 缺少必要的gewechat配置: {', '.join(missing_configs)}")

    def get_image_data(self, msg):
        """获取图片数据"""
        if conf().get("channel_type") != "gewechat":
            return None
            
        try:
            from lib.gewechat import GewechatClient
            
            # 获取配置
            app_id = conf().get('gewechat_app_id')
            base_url = conf().get("gewechat_base_url")
            token = conf().get("gewechat_token")
            download_url = conf().get("gewechat_download_url")
            
            if not all([app_id, base_url, token, download_url]):
                return None
            
            # 获取XML内容
            content_xml = msg._rawmsg['Data']['Content']['string']
            xml_start = content_xml.find('<?xml version=')
            if xml_start != -1:
                content_xml = content_xml[xml_start:]
            
            # 下载图片
            client = GewechatClient(base_url, token)
            image_info = client.download_image(app_id=app_id, xml=content_xml, type=1)
            
            if image_info.get('ret') != 200:
                image_info = client.download_image(app_id=app_id, xml=content_xml, type=2)
            
            if image_info.get('ret') == 200 and image_info.get('data'):
                file_url = image_info['data']['fileUrl']
                full_url = f"{download_url.rstrip('/')}/{file_url}"
                
                response = requests.get(full_url)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode('utf-8')
                    
        except Exception as e:
            logger.error(f"[GeImg2Url] 图片获取失败: {e}")
        return None

    def upload_to_imgbb(self, base64_image):
        """上传图片到ImgBB"""
        if not self.imgbb_api_key or not base64_image:
            return None
            
        try:
            response = requests.post(
                'https://api.imgbb.com/1/upload',
                data={
                    'key': self.imgbb_api_key,
                    'image': base64_image
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('data', {}).get('url')
                    
        except Exception as e:
            logger.error(f"[GeImg2Url] 图片上传失败: {e}")
        return None

    def on_handle_context(self, e_context):
        content = e_context['context'].content
        msg = e_context['context']['msg']
        
        if not msg.from_user_id:
            return
            
        if e_context['context'].type == ContextType.TEXT and self.trigger_word in content:
            self.waiting_for_image[msg.from_user_id] = True
            e_context['reply'] = Reply(ReplyType.TEXT, "请发送需要转换的图片")
            e_context.action = EventAction.BREAK_PASS
            return
            
        if e_context['context'].type == ContextType.IMAGE and msg.from_user_id in self.waiting_for_image:
            base64_data = self.get_image_data(msg)
            if not base64_data:
                e_context['reply'] = Reply(ReplyType.ERROR, "无法获取图片数据，请确保使用gewechat通道")
                return
                
            image_url = self.upload_to_imgbb(base64_data)
            if not image_url:
                e_context['reply'] = Reply(ReplyType.ERROR, "上传图片失败")
                return
                
            url_text = f"====== 图片上传成功 ======\n链接: {image_url}\n====================="
            e_context['reply'] = Reply(ReplyType.TEXT, url_text)
            e_context['context'].kwargs['no_image_parse'] = True
            e_context.action = EventAction.BREAK_PASS
            del self.waiting_for_image[msg.from_user_id]

    def get_help_text(self, **kwargs):
        help_text = "图片转链接插件使用说明：\n"
        help_text += "1. 发送'图转链接'，收到反馈消息后再发送图片\n"
        help_text += "2. 插件会自动上传图片并返回可访问的URL\n"
        help_text += "注意：仅支持gewechat通道使用\n"
        return help_text