# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.
    import requests
    import chardet

    # 1. 下载文件
    url = "http://172.18.192.75:8091/tqlab/dataresource/downloadDataFile?dbName=meta_data&tableName=stock_code"
    response = requests.get(url)
    content = response.content

    # 2. 用chardet检测编码
    result = chardet.detect(content)
    print(f"chardet检测结果: {result}")

    # 3. 尝试用检测出的编码解码并打印前几行
    try:
        encoding = result['encoding']
        text = content.decode(encoding)
        lines = text.splitlines()
        for i, line in enumerate(lines[:5]):
            print(f"第{i+1}行: {line}")
    except Exception as e:
        print(f"解码失败: {e}")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
