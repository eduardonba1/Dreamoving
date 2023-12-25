import sys
import os
import json

is_test_gradio = False
is_wanx_platform = False
VERSION = "1.1.8"

scale_depth = 0.7
scale_pose = 0.5

DASHONE_SERVICE_ID = os.getenv('DASHONE_SERVICE_ID')
OSSAccessKeyId = os.getenv('OSSAccessKeyId')
OSSAccessKeySecret = os.getenv('OSSAccessKeySecret')
EAS_AUTH_CARTOONRECOG = os.getenv('EAS_AUTH_CARTOONRECOG')
EAS_AUTH_PROMPT = os.getenv('EAS_AUTH_PROMPT')

num_instance_dashone = 10
avg_process_time = 4.3 # 7 # minutes
ref_video_path = 'data/origin_video/video'
ref_video_prompt = 'data/origin_video/video_prompts_cn.txt'

class RESOURCES:
    logo_img0 = "https://vibktprfx-prod-prod-xstream-cn-shanghai.oss-cn-shanghai.aliyuncs.com/xstream-framework/code/humangen-2023-11-02/logo/title0.jpg?OSSAccessKeyId=LTAI5tQyVREDrxAdmaeuNfcW&Expires=1705605234&Signature=s759XKL4NEBHS8SPMRjIw1U%2FWr4%3D"
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
"template_31.mp4":'一个女孩，在秋天的公园里跳舞，穿着长款灰色T恤和长袖。',
"template_38.mp4":'一个男人，在时代广场，穿着衬衫和西装。',
"template_41.mp4":'一位女孩，身穿圣诞老人装，长袖红裤，置身于童话小镇。',
"template_43.mp4":'一位男士，身穿圣诞老人装，长袖红裤，置身于童话小镇。',
"template_46.mp4":'一位女孩，面带微笑，在桌子前跳舞，桌上有绿植，身穿长毛衣和牛仔裤。',
"template_51.mp4":'一位女孩，站在中央公园，身穿白色毛衣和牛仔裤。',
"template_67.mp4":'有一个女人穿着裙子在覆盖着雪的童话小镇上跳舞。',
"template_81.mp4":'一位女孩，穿着白色衬衫和蓝色短裤，在有壁炉的温暖公寓中跳舞。',
"template_100.mp4":'一位女孩，在海边沙滩上跳舞，穿着长袖白色连衣裙。',
}

# RELEASE_NOTE = '''使用说明（2023/12/18）
#     1、...
# '''
