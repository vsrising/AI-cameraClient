import pika
import base64
import os
import ast
from datetime import datetime

def callback(ch, method, properties, body):
    # 将消息体从字符串转换为字典格式
    message = ast.literal_eval(body.decode('utf-8'))  # 解析字符串为字典
    camera_index = message['camera_index']  # 获取摄像头编号
    timestamp = message['timestamp']        # 获取时间戳
    encoded_image = message['image']        # 获取 Base64 编码的图片

    # 创建对应摄像头编号的文件夹
    folder_name = f"camera_{camera_index}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # 使用时间戳生成唯一的文件名
    timestamp_str = timestamp.replace(" ", "_").replace(":", "")
    image_filename = f"{folder_name}/alert_{timestamp_str}.png"

    # 将 Base64 编码的图片解码
    decoded_image = base64.b64decode(encoded_image)

    # 将解码后的图片保存为文件
    with open(image_filename, "wb") as image_file:
        image_file.write(decoded_image)

    print(f" [x] Received and saved image alert from camera {camera_index} at {timestamp} as '{image_filename}'")

# 连接到 RabbitMQ 服务器
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# 声明队列
channel.queue_declare(queue='camera_alerts')

# 告诉 RabbitMQ 该消费者将从队列接收图片
channel.basic_consume(queue='camera_alerts',
                      on_message_callback=callback,
                      auto_ack=True)

print(' [*] Waiting for image alerts. To exit press CTRL+C')
channel.start_consuming()
