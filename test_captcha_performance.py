#!/usr/bin/env python3
"""
验证码性能测试脚本
用于测试验证码生成速度和稳定性
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor
import statistics

def test_captcha_performance():
    """测试验证码API性能"""
    base_url = "http://localhost:5000"  # 假设应用运行在本地5000端口
    
    print("🚀 开始验证码性能测试...")
    
    # 单次请求测试
    print("\n📊 单次请求测试:")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/api/captcha", timeout=10)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            processing_time = float(data.get('processing_time', '0').replace('ms', ''))
            print(f"✅ 成功 - 状态码: {response.status_code}")
            print(f"   服务器处理时间: {processing_time}ms")
            print(f"   总耗时: {(end_time - start_time) * 1000:.2f}ms")
            print(f"   图片数据长度: {len(data.get('image', ''))} 字符")
        else:
            print(f"❌ 失败 - 状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时 (10秒)")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请确保应用正在运行")
    except Exception as e:
        print(f"❌ 其他错误: {e}")
    
    # 并发测试
    print("\n⚡ 并发性能测试 (5个并发请求):")
    
    def make_request():
        try:
            start = time.time()
            response = requests.get(f"{base_url}/api/captcha", timeout=15)
            end = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'processing_time': float(data.get('processing_time', '0').replace('ms', '')),
                    'total_time': (end - start) * 1000,
                    'image_size': len(data.get('image', ''))
                }
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # 执行5个并发请求
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [future.result() for future in futures]
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"   成功: {len(successful)} 个请求")
    print(f"   失败: {len(failed)} 个请求")
    
    if successful:
        processing_times = [r['processing_time'] for r in successful]
        total_times = [r['total_time'] for r in successful]
        
        print(f"   平均处理时间: {statistics.mean(processing_times):.2f}ms")
        print(f"   最快处理时间: {min(processing_times):.2f}ms")
        print(f"   最慢处理时间: {max(processing_times):.2f}ms")
        print(f"   平均总耗时: {statistics.mean(total_times):.2f}ms")
        print(f"   图片平均大小: {statistics.mean([r['image_size'] for r in successful]):.0f} 字符")
    
    if failed:
        print("\n❌ 失败详情:")
        for i, result in enumerate(failed, 1):
            print(f"   请求 {i}: {result['error']}")
    
    # 连续稳定性测试
    print("\n🔍 连续稳定性测试 (10个顺序请求):")
    
    stability_results = []
    for i in range(1, 11):
        try:
            start = time.time()
            response = requests.get(f"{base_url}/api/captcha", timeout=10)
            end = time.time()
            
            if response.status_code == 200:
                data = response.json()
                processing_time = float(data.get('processing_time', '0').replace('ms', ''))
                stability_results.append({
                    'success': True,
                    'processing_time': processing_time,
                    'total_time': (end - start) * 1000
                })
                print(f"   请求 {i}: ✅ 成功 - {processing_time:.2f}ms")
            else:
                stability_results.append({'success': False})
                print(f"   请求 {i}: ❌ 失败 - HTTP {response.status_code}")
                
        except Exception as e:
            stability_results.append({'success': False})
            print(f"   请求 {i}: ❌ 异常 - {e}")
        
        # 短暂间隔，避免服务器压力过大
        time.sleep(0.5)
    
    successful_stability = [r for r in stability_results if r['success']]
    if successful_stability:
        proc_times = [r['processing_time'] for r in successful_stability]
        print(f"\n📈 稳定性测试结果:")
        print(f"   成功率: {len(successful_stability)}/{len(stability_results)} ({len(successful_stability)/len(stability_results)*100:.1f}%)")
        print(f"   平均处理时间: {statistics.mean(proc_times):.2f}ms")
        print(f"   时间标准差: {statistics.stdev(proc_times) if len(proc_times) > 1 else 0:.2f}ms")
    
    print("\n🎯 测试完成!")

if __name__ == "__main__":
    test_captcha_performance()