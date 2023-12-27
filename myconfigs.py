import sys
import os
import json

is_test_gradio = False
is_wanx_platform = False
VERSION = "1.1.9"

scale_depth = 0.7
scale_pose = 0.5

DASHONE_SERVICE_ID = os.getenv('DASHONE_SERVICE_ID')
OSSAccessKeyId = os.getenv('OSSAccessKeyId')
OSSAccessKeySecret = os.getenv('OSSAccessKeySecret')
OSSEndpoint = os.getenv('OSSEndpoint')
OSSBucketName = os.getenv('OSSBucketName')
OSSObjectName = os.getenv('OSSObjectName')
EAS_AUTH_CARTOONRECOG = os.getenv('EAS_AUTH_CARTOONRECOG')
EAS_AUTH_PROMPT = os.getenv('EAS_AUTH_PROMPT')
TRANSLATE_CN_EN = os.getenv('TRANSLATE_CN_EN')

num_instance_dashone = 2
avg_process_time = 5 # minutes
ref_video_path = 'data/origin_video/video'
ref_video_prompt = 'data/origin_video/video_prompts_en.txt'

class RESOURCES:
    logo_img0 = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/dreamoving.jpg?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1707180774&Signature=WSmhiJ2RWgFMoMQ2rf0VOvCkIY8%3D"
    logo_img1 = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/title1.jpg?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1705605528&Signature=Nv8MYnkZd%2F45GZA2tCZFtu6cREM%3D"
    logo_img2 = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/title2.png?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1705605598&Signature=ac0P4ENqTrlWG73fYhfaYUR551o%3D"
    logo_dingding = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/dingdingqun.jpg?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1706503081&Signature=133WdLAWzsBQzqIWvD5yXcsP69I%3D"
    logo_wechat = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/weixinqun.jpg?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1703759402&Signature=sBPLGvpWLoilqFswqTlodI6KwdY%3D"
    
examples = {
    'examples_images': [
        ['./data/img/cfpcgcsg.jpg'],
        ['./data/img/md_0.png'],
        ['./data/img/30.jpg'],
        ['./data/img/mod_2.jpeg'],
        ['./data/img/hailuo_718746736_RF.jpg'],
        ['./data/img/mod_3.png'],
        ['./data/img/mod_13.png'],
        ['./data/img/hailuo_2238672930_RF.jpg'],
        ['./data/img/bmy.png'],
    ],
    'template_video': [
        'template_31.mp4',
        'template_41.mp4',
        'template_51.mp4',
        'template_46.mp4',
        'template_43.mp4',
        'template_38.mp4',
        'template_67.mp4',
        'template_81.mp4',
        'template_100.mp4',
    ],
}
template_orign_videos = {
'template_31.mp4':'./data/origin_video/video/31.mp4',
'template_38.mp4':'./data/origin_video/video/48.mp4',
'template_41.mp4':'./data/origin_video/video/41.mp4',
'template_43.mp4':'./data/origin_video/video/43.mp4',
'template_46.mp4':'./data/origin_video/video/46.mp4',
'template_51.mp4':'./data/origin_video/video/51.mp4',
'template_67.mp4':'./data/origin_video/video/67.mp4',
'template_81.mp4':'./data/origin_video/video/81.mp4',
'template_100.mp4':'./data/origin_video/video/100.mp4',
}
template_prompts = {
"template_31.mp4":'a girl, dancing in the park in autumn, wear long gray t-shirt with long sleeves.',
"template_38.mp4":'a man, in Times Square, wearing shirt and suit.',
"template_41.mp4":'a girl, in a fairytale town, wearing Santa clause costume, long sleeves, red pants.',
"template_43.mp4":'a man, in a fairytale town, wearing Santa clause costume, long sleeves, red pants.',
"template_46.mp4":'a girl, smiling, dancing in front of a desk with green plants, wearing long sweater and jeans.',
"template_51.mp4":'a girl, standing in central park, wearing a white sweater and jeans.',
"template_67.mp4":'there is a woman in a skirt dancing in a fairytale town covered in snow.',
"template_81.mp4":'a girl in a white shirt and blue shorts is dancing, in an warm apartment with a fireplace.',
"template_100.mp4":'a girl, dancing on a beach next to the ocean, wearing a white dress with long sleeves.',
}
