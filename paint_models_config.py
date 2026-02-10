#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI大模型配置文件模板
包含所有主流AI图像生成模型的默认配置
"""

# 主流AI模型的默认配置
AI_MODEL_CONFIGS = {
    '豆包-Seedream': {
        'api_base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'image_endpoint': '/images/generations',
        'model_name': 'doubao-seedream-4-5-251128',
        'api_key': 'user-modified-api-key-12345',
        'timeout': 60,
        'image_size': '2048x1800',
        'n': 1,
        'quality': 'standard',
        'style': 'vivid',
        'description': '字节跳动豆包AI，国内领先的图像生成模型',
        'max_tokens': 2048,
        'temperature': 70,
        'quality_level': 7
    },
    
    'Midjourney': {
        'api_base_url': 'https://api.midjourney.com/v1',
        'image_endpoint': '/imagine',
        'model_name': 'midjourney-v6',
        'api_key': 'your-midjourney-api-key',
        'timeout': 120,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'hd',
        'style': 'vivid',
        'description': 'Midjourney，最受欢迎的AI艺术生成工具',
        'max_tokens': 2048,
        'temperature': 75,
        'quality_level': 9
    },
    
    'Stable Diffusion': {
        'api_base_url': 'https://api.stability.ai/v1',
        'image_endpoint': '/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
        'model_name': 'stable-diffusion-xl-1024-v1-0',
        'api_key': 'your-stability-ai-api-key',
        'timeout': 90,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': 'Stability AI的Stable Diffusion，开源图像生成模型',
        'max_tokens': 2048,
        'temperature': 60,
        'quality_level': 8
    },
    
    'DALL-E 3': {
        'api_base_url': 'https://api.openai.com/v1',
        'image_endpoint': '/images/generations',
        'model_name': 'dall-e-3',
        'api_key': 'your-openai-api-key',
        'timeout': 60,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'hd',
        'style': 'vivid',
        'description': 'OpenAI的DALL-E 3，最先进的图像生成模型之一',
        'max_tokens': 2048,
        'temperature': 80,
        'quality_level': 10
    },
    
    'Adobe Firefly': {
        'api_base_url': 'https://firefly-api.adobe.com/v1',
        'image_endpoint': '/images/generate',
        'model_name': 'firefly-v2',
        'api_key': 'your-adobe-firefly-api-key',
        'timeout': 80,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': 'Adobe Firefly，专业级的AI图像生成工具',
        'max_tokens': 2048,
        'temperature': 65,
        'quality_level': 8
    },
    
    'Leonardo AI': {
        'api_base_url': 'https://cloud.leonardo.ai/api/rest/v1',
        'image_endpoint': '/generations',
        'model_name': 'leonardo-diffusion-xl',
        'api_key': 'your-leonardo-ai-api-key',
        'timeout': 90,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'hd',
        'style': 'vivid',
        'description': 'Leonardo AI，专注于游戏和艺术创作的AI平台',
        'max_tokens': 2048,
        'temperature': 70,
        'quality_level': 8
    },
    
    'Bing Image Creator': {
        'api_base_url': 'https://www.bing.com/images/create',
        'image_endpoint': '/api/create',
        'model_name': 'bing-dall-e',
        'api_key': 'your-bing-api-key',
        'timeout': 60,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': '微软Bing图像创建器，基于DALL-E的免费服务',
        'max_tokens': 1024,
        'temperature': 50,
        'quality_level': 6
    },
    
    'Canva AI': {
        'api_base_url': 'https://api.canva.com/rest/v1',
        'image_endpoint': '/ai/image/generate',
        'model_name': 'canva-magic-media',
        'api_key': 'your-canva-api-key',
        'timeout': 70,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'vivid',
        'description': 'Canva的AI图像生成，集成在设计工具中',
        'max_tokens': 1024,
        'temperature': 60,
        'quality_level': 7
    },
    
    'Runway ML': {
        'api_base_url': 'https://api.runwayml.com/v1',
        'image_endpoint': '/generate',
        'model_name': 'runway-gen2',
        'api_key': 'your-runway-ml-api-key',
        'timeout': 120,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'hd',
        'style': 'vivid',
        'description': 'Runway ML，专注于视频和图像生成的AI平台',
        'max_tokens': 2048,
        'temperature': 75,
        'quality_level': 9
    },
    
    'Craiyon': {
        'api_base_url': 'https://api.craiyon.com/v1',
        'image_endpoint': '/generate',
        'model_name': 'craiyon-v3',
        'api_key': 'your-craiyon-api-key',
        'timeout': 60,
        'image_size': '512x512',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': 'Craiyon（原DALL-E mini），免费的AI图像生成器',
        'max_tokens': 1024,
        'temperature': 55,
        'quality_level': 5
    },
    
    'DreamStudio': {
        'api_base_url': 'https://api.stability.ai/v1',
        'image_endpoint': '/generation/stable-diffusion-v1-6/text-to-image',
        'model_name': 'stable-diffusion-v1-6',
        'api_key': 'your-stability-api-key',
        'timeout': 90,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': 'Stability AI的官方平台，基于Stable Diffusion',
        'max_tokens': 2048,
        'temperature': 65,
        'quality_level': 8
    },
    
    '文心一格': {
        'api_base_url': 'https://wenxin.baidu.com/younger/portal/apiRestProxy/v1',
        'image_endpoint': '/txt2img',
        'model_name': 'wenxin-yige',
        'api_key': 'your-baidu-wenxin-api-key',
        'timeout': 80,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'vivid',
        'description': '百度文心一格，中文AI图像生成模型',
        'max_tokens': 1024,
        'temperature': 60,
        'quality_level': 7
    },
    
    '通义万相': {
        'api_base_url': 'https://dashscope.aliyuncs.com/api/v1',
        'image_endpoint': '/services/aigc/text2image/image-synthesis',
        'model_name': 'wanx-v1',
        'api_key': 'your-alibaba-wanx-api-key',
        'timeout': 90,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'vivid',
        'description': '阿里云通义万相，中文AI图像生成服务',
        'max_tokens': 1024,
        'temperature': 65,
        'quality_level': 7
    },
    
    '讯飞星火': {
        'api_base_url': 'https://xinghuo.xfyun.cn/api/v1',
        'image_endpoint': '/image/generate',
        'model_name': 'spark-img-v2',
        'api_key': 'your-xfyun-spark-api-key',
        'timeout': 70,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': '科大讯飞星火大模型，支持图像生成',
        'max_tokens': 1024,
        'temperature': 60,
        'quality_level': 6
    },
    
    '智谱AI': {
        'api_base_url': 'https://open.bigmodel.cn/api/paas/v1',
        'image_endpoint': '/images/generations',
        'model_name': 'cogview-3',
        'api_key': 'your-zhipu-ai-api-key',
        'timeout': 80,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'vivid',
        'description': '智谱AI的CogView，中文AI图像生成模型',
        'max_tokens': 1024,
        'temperature': 65,
        'quality_level': 7
    },
    
    '商汤秒画': {
        'api_base_url': 'https://api.sensetime.com/v1',
        'image_endpoint': '/miaohua/generate',
        'model_name': 'sensetime-miaohua',
        'api_key': 'your-sensetime-api-key',
        'timeout': 90,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'hd',
        'style': 'vivid',
        'description': '商汤秒画，专业级AI图像生成服务',
        'max_tokens': 2048,
        'temperature': 70,
        'quality_level': 9
    },
    
    '昆仑天工': {
        'api_base_url': 'https://api.tiangong.cn/v1',
        'image_endpoint': '/image/generate',
        'model_name': 'tiangong-paint',
        'api_key': 'your-tiangong-api-key',
        'timeout': 80,
        'image_size': '1024x1024',
        'n': 1,
        'quality': 'standard',
        'style': 'natural',
        'description': '昆仑万维天工，中文AI图像生成模型',
        'max_tokens': 1024,
        'temperature': 60,
        'quality_level': 6
    }
}

# 生成INI格式配置文件的函数
def generate_ini_config():
    """生成完整的INI配置文件内容"""
    config_content = "# AI大模型配置文件\n# 包含主流AI图像生成服务的配置参数\n\n"
    
    for model_name, config in AI_MODEL_CONFIGS.items():
        # 将模型名称转换为INI格式的section名称
        section_name = model_name.replace(' ', '_').replace('-', '_')
        config_content += f"[{section_name}]\n"
        config_content += f"# {config['description']}\n"
        
        for key, value in config.items():
            if key != 'description':  # 跳过描述，只保留实际配置
                config_content += f"{key} = {value}\n"
        
        config_content += "\n"
    
    return config_content

# 获取指定模型的配置
def get_model_config(model_name):
    """获取指定模型的配置"""
    return AI_MODEL_CONFIGS.get(model_name, AI_MODEL_CONFIGS['豆包-Seedream'])

# 获取所有可用模型列表
def get_available_models():
    """获取所有可用模型列表"""
    return list(AI_MODEL_CONFIGS.keys())

if __name__ == '__main__':
    # 生成并保存配置文件
    ini_content = generate_ini_config()
    
    with open('ai_models_config.ini', 'w', encoding='utf-8') as f:
        f.write(ini_content)
    
    print("AI模型配置文件已生成: ai_models_config.ini")
    print(f"共包含 {len(AI_MODEL_CONFIGS)} 个主流AI模型的配置")
    
    # 显示可用模型
    print("\n可用模型列表:")
    for i, model in enumerate(get_available_models(), 1):
        print(f"{i}. {model}")
    
    # 测试获取配置
    print(f"\n豆包配置示例:")
    config = get_model_config('豆包-Seedream')
    for key, value in config.items():
        print(f"  {key}: {value}")