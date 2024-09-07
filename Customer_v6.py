import pika
import base64
import os
import ast
import mysql.connector
from datetime import datetime

# MySQL 配置
db_config = {
    'user': 'root',
    'password': 'yulanrui',
    'host': 'localhost',
    'database': 'ry-vue',
    'port': 3306  # 如果你使用的是默认端口3306
}

# 连接 MySQL 数据库
def connect_to_mysql():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# 将图片地址存入 MySQL 数据库
def save_to_database(camera_index, timestamp, image_path,dev_seriesid,detection_count):
    connection = connect_to_mysql()
    if connection is None:
        print("Failed to connect to the database.")
        return

    try:
        cursor = connection.cursor()
        # 插入摄像头告警记录到数据库
        insert_query = "INSERT INTO camera_alerts (camera_index, timestamp, image_path, dev_seriesid,detection_count) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (camera_index, timestamp, image_path, dev_seriesid, detection_count))
        connection.commit()
        print(f" [x] Record saved to database: {image_path}")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

# RabbitMQ 回调函数，处理接收到的图片
def callback(ch, method, properties, body):
    # 将消息体从字符串转换为字典格式
    message = ast.literal_eval(body.decode('utf-8'))  # 解析字符串为字典
    #camera_index = message['camera_index']  # 获取摄像头编号
    camera_index = 1  # 获取摄像头编号
    timestamp = message['timestamp']        # 获取时间戳
    encoded_image = message['image']        # 获取 Base64 编码的图片
    dev_seriesid = message['seriesid']          # 获取设备id
    detection_count = message['detection_count']    #监测次数

    # 创建对应摄像头编号的文件夹
    path = 'C:\\Users\\Richasun\\Downloads\\xl\\uploadPath\\upload\\'
    folder_name = path+f"camera_{camera_index}"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # 使用时间戳生成唯一的文件名
    timestamp_str = timestamp.replace(" ", "_").replace(":", "")
    image_filename = f"{folder_name}/alert_{timestamp_str}.png"
    image_path = '/profile/upload/' + f"camera_{camera_index}"+f"/alert_{timestamp_str}.png"

    # 将 Base64 编码的图片解码
    decoded_image = base64.b64decode(encoded_image)

    # 将解码后的图片保存为文件
    with open(image_filename, "wb") as image_file:
        image_file.write(decoded_image)

    print(f" [x] Received and saved image alert from camera {camera_index} at {timestamp} as '{image_filename}'")

    # 将图片路径和相关信息存储到数据库
    save_to_database(camera_index, timestamp, image_path,dev_seriesid,detection_count)

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
