import pika
import base64
from datetime import datetime

# 初始化一个计数器
counter = 0

def callback(ch, method, properties, body):
    global counter
    counter += 1
    # 获取当前时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 使用计数器和时间戳生成唯一的文件名
    image_filename = f"received_camera_alert_image_{counter}_{timestamp}.png"

    # 将 Base64 编码的图片解码
    decoded_image = base64.b64decode(body)

    # 将解码后的图片保存为文件
    with open(image_filename, "wb") as image_file:
        image_file.write(decoded_image)

    print(f" [x] Received and saved image alert as 'received_camera_alert_image.png'")


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
