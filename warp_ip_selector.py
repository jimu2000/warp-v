import requests
import time
import threading
import json
import random
import socket
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('warp_ip_selector.log'), logging.StreamHandler()]
)

class WARPIPSelector:
    def __init__(self):
        self.ip_list = []
        self.result_list = []
        self.threads = []
        self.timeout = 5  # 超时时间，单位秒
        self.thread_num = 100  # 线程数量
        self.save_file = "warp_best_ips.json"
        self.test_url = "https://www.cloudflare.com/cdn-cgi/trace"  # Cloudflare官方测试URL
        self.cloudflare_ips_file = "cloudflare_ips.txt"
        
    def load_cloudflare_ips(self):
        """从Cloudflare官方获取IP段并生成测试IP列表"""
        try:
            logging.info("正在从Cloudflare官方获取IP段...")
            response = requests.get("https://www.cloudflare.com/ips-v4")
            if response.status_code != 200:
                logging.error(f"获取Cloudflare IP段失败，状态码: {response.status_code}")
                return False
                
            ip_ranges = response.text.strip().split("\n")
            # 随机从每个IP段中选择一些IP
            for ip_range in ip_ranges:
                if "/" in ip_range:
                    ip, mask = ip_range.split("/")
                    mask = int(mask)
                    if mask >= 24:  # 只处理足够大的网段
                        # 生成该网段中的随机IP
                        for _ in range(5):  # 每个网段随机选5个IP
                            parts = list(map(int, ip.split(".")))
                            # 随机生成最后几位
                            if mask == 24:
                                parts[3] = random.randint(1, 254)
                            elif mask == 23:
                                parts[2] += random.randint(0, 1)
                                parts[3] = random.randint(1, 254)
                            self.ip_list.append(".".join(map(str, parts)))
            logging.info(f"已生成 {len(self.ip_list)} 个测试IP")
            return True
        except Exception as e:
            logging.error(f"获取Cloudflare IP段时出错: {str(e)}")
            return False
    
    def test_single_ip(self, ip):
        """测试单个IP的延迟和可用性"""
        try:
            start_time = time.time()
            # 尝试解析IP
            socket.gethostbyname(ip)
            
            # 测试连接
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((ip, 443))  # 测试HTTPS端口
                
            # 测试速度
            response = requests.get(f"https://{ip}/cdn-cgi/trace", timeout=self.timeout)
            if response.status_code == 200:
                elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
                logging.debug(f"IP: {ip}, 响应时间: {elapsed_time:.2f}ms")
                self.result_list.append({
                    "ip": ip,
                    "response_time": elapsed_time,
                    "available": True
                })
        except Exception as e:
            logging.debug(f"IP: {ip}, 测试失败: {str(e)}")
            self.result_list.append({
                "ip": ip,
                "response_time": float('inf'),
                "available": False
            })
    
    def run_tests(self):
        """运行所有IP测试"""
        if not self.ip_list:
            if not self.load_cloudflare_ips():
                logging.error("无法获取测试IP列表，程序退出")
                return False
                
        logging.info(f"开始测试 {len(self.ip_list)} 个IP，使用 {self.thread_num} 个线程...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
            executor.map(self.test_single_ip, self.ip_list)
        
        elapsed_time = time.time() - start_time
        logging.info(f"测试完成，耗时: {elapsed_time:.2f}秒")
        return True
    
    def get_best_ips(self, count=10):
        """获取最佳的几个IP"""
        if not self.result_list:
            logging.warning("没有测试结果可供筛选")
            return []
            
        # 按响应时间排序
        sorted_ips = sorted(
            [ip for ip in self.result_list if ip["available"]],
            key=lambda x: x["response_time"]
        )
        
        if not sorted_ips:
            logging.warning("没有找到可用的IP")
            return []
            
        best_ips = sorted_ips[:count]
        logging.info(f"最佳 {len(best_ips)} 个IP已选出")
        for i, ip_info in enumerate(best_ips, 1):
            logging.info(f"{i}. IP: {ip_info['ip']}, 响应时间: {ip_info['response_time']:.2f}ms")
        
        return best_ips
    
    def save_to_file(self, best_ips):
        """保存最佳IP到文件"""
        try:
            with open(self.save_file, "w") as f:
                json.dump(best_ips, f, indent=4)
            logging.info(f"最佳IP已保存到 {self.save_file}")
            return True
        except Exception as e:
            logging.error(f"保存文件时出错: {str(e)}")
            return False
    
    def load_from_file(self):
        """从文件加载最佳IP"""
        try:
            if Path(self.save_file).exists():
                with open(self.save_file, "r") as f:
                    data = json.load(f)
                logging.info(f"从 {self.save_file} 加载了 {len(data)} 个IP")
                return data
            else:
                logging.warning(f"文件 {self.save_file} 不存在")
                return []
        except Exception as e:
            logging.error(f"加载文件时出错: {str(e)}")
            return []

if __name__ == "__main__":
    selector = WARPIPSelector()
    
    # 可以选择从文件加载已有结果
    # best_ips = selector.load_from_file()
    # if not best_ips:
    
    # 或者运行新的测试
    if selector.run_tests():
        best_ips = selector.get_best_ips(20)  # 获取前20个最佳IP
        if best_ips:
            selector.save_to_file(best_ips)
            print("\n优选IP结果:")
            for i, ip_info in enumerate(best_ips, 1):
                print(f"{i}. {ip_info['ip']} - 响应时间: {ip_info['response_time']:.2f}ms")
        else:
            print("没有找到可用的IP，请检查网络连接或调整参数")
    else:
        print("IP测试运行失败，请查看日志获取详细信息")    