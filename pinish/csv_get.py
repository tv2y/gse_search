import csv
import os

def extract_urls_from_csv(input_file, output_file, url_column_name):
    """
    从 CSV 文件中提取指定列的 URL 并保存到 TXT 文件。
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f_in:
        # 使用 DictReader 可以直接通过列名访问数据
        reader = csv.DictReader(f_in)

        with open(output_file, mode='w', encoding='utf-8') as f_out:
            for row in reader:
                url = row.get(url_column_name)
                if url:
                    f_out.write(url + '\n')

def main(input_file, output_file, url_column_name):
    """
    主函数：配置输入输出并执行提取。
    """
    extract_urls_from_csv(input_file, output_file, url_column_name)
    print(f"提取完成，URL 已保存至 {output_file}")

if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    # 使用相对路径
    INPUT_FILE = 'verified_online.csv'
    OUTPUT_FILE = 'pinish_urls.txt'
    URL_COLUMN_NAME = 'url'
    
    main(INPUT_FILE, OUTPUT_FILE, URL_COLUMN_NAME)
