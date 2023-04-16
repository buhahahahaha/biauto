import requests

# 웹훅 URL
webhook_url = 'https://discordapp.com/api/webhooks/1095655937735413772/pmE27Cok8_W-arSpcpwfhE_uOm_h5VQZG-gbv-vWnUk1cs9H6x3TBPpWPo49KWaqTRo_'

# 메시지 전송
mes = {'content': '오류발생'}

response = requests.post(webhook_url, json=mes)

if response.status_code == 204:
    print('메시지가 성공적으로 전송되었습니다.')
else:
    print('메시지 전송 실패:', response.status_code, response.text)