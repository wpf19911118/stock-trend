#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据缓存模块
提供数据缓存和读取功能，减少API调用次数
"""

import json
import pickle
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict
import pandas as pd


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "./cache", expire_hours: int = 6):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            expire_hours: 缓存过期时间（小时）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.expire_hours = expire_hours
        
        # 子目录
        self.json_cache_dir = self.cache_dir / "json"
        self.df_cache_dir = self.cache_dir / "dataframes"
        self.json_cache_dir.mkdir(exist_ok=True)
        self.df_cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_key(self, prefix: str, params: Dict) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 缓存前缀
            params: 参数字典
        
        Returns:
            缓存键字符串
        """
        param_str = json.dumps(params, sort_keys=True)
        hash_key = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}_{hash_key}"
    
    def _is_expired(self, cache_file: Path) -> bool:
        """
        检查缓存是否过期
        
        Args:
            cache_file: 缓存文件路径
        
        Returns:
            是否过期
        """
        if not cache_file.exists():
            return True
        
        # 获取文件修改时间
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        expire_time = mtime + timedelta(hours=self.expire_hours)
        
        return datetime.now() > expire_time
    
    def get(self, prefix: str, params: Dict) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            prefix: 缓存前缀
            params: 参数字典
        
        Returns:
            缓存数据或None
        """
        cache_key = self._get_cache_key(prefix, params)
        cache_file = self.json_cache_dir / f"{cache_key}.json"
        
        if self._is_expired(cache_file):
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📦 使用缓存数据: {prefix}")
                return data
        except Exception as e:
            print(f"⚠️ 读取缓存失败: {e}")
            return None
    
    def set(self, prefix: str, params: Dict, data: Any):
        """
        设置缓存数据
        
        Args:
            prefix: 缓存前缀
            params: 参数字典
            data: 要缓存的数据
        """
        cache_key = self._get_cache_key(prefix, params)
        cache_file = self.json_cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"⚠️ 写入缓存失败: {e}")
    
    def get_dataframe(self, prefix: str, params: Dict) -> Optional[pd.DataFrame]:
        """
        获取缓存的DataFrame
        
        Args:
            prefix: 缓存前缀
            params: 参数字典
        
        Returns:
            DataFrame或None
        """
        cache_key = self._get_cache_key(prefix, params)
        cache_file = self.df_cache_dir / f"{cache_key}.pkl"
        
        if self._is_expired(cache_file):
            return None
        
        try:
            with open(cache_file, "rb") as f:
                df = pickle.load(f)
                print(f"📦 使用缓存DataFrame: {prefix}")
                return df
        except Exception as e:
            print(f"⚠️ 读取DataFrame缓存失败: {e}")
            return None
    
    def set_dataframe(self, prefix: str, params: Dict, df: pd.DataFrame):
        """
        设置缓存的DataFrame
        
        Args:
            prefix: 缓存前缀
            params: 参数字典
            df: 要缓存的DataFrame
        """
        cache_key = self._get_cache_key(prefix, params)
        cache_file = self.df_cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(df, f)
        except Exception as e:
            print(f"⚠️ 写入DataFrame缓存失败: {e}")
    
    def clear_expired(self):
        """
        清理过期缓存
        """
        count = 0
        
        # 清理JSON缓存
        for cache_file in self.json_cache_dir.glob("*.json"):
            if self._is_expired(cache_file):
                cache_file.unlink()
                count += 1
        
        # 清理DataFrame缓存
        for cache_file in self.df_cache_dir.glob("*.pkl"):
            if self._is_expired(cache_file):
                cache_file.unlink()
                count += 1
        
        if count > 0:
            print(f"🗑️ 清理了 {count} 个过期缓存文件")
    
    def clear_all(self):
        """
        清理所有缓存
        """
        count = 0
        
        for cache_file in self.json_cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        
        for cache_file in self.df_cache_dir.glob("*.pkl"):
            cache_file.unlink()
            count += 1
        
        print(f"🗑️ 清理了所有 {count} 个缓存文件")


# 全局缓存实例
cache = DataCache()


def get_cached_data(prefix: str, params: Dict, fetch_func, use_cache: bool = True) -> Any:
    """
    获取缓存数据或重新获取
    
    Args:
        prefix: 缓存前缀
        params: 参数字典
        fetch_func: 获取数据的函数
        use_cache: 是否使用缓存
    
    Returns:
        数据
    """
    if use_cache:
        # 尝试从缓存获取
        cached_data = cache.get(prefix, params)
        if cached_data is not None:
            return cached_data
    
    # 重新获取数据
    print(f"🌐 从API获取数据: {prefix}")
    data = fetch_func()
    
    # 存入缓存
    if use_cache and data is not None:
        cache.set(prefix, params, data)
    
    return data


def get_cached_dataframe(prefix: str, params: Dict, fetch_func, use_cache: bool = True) -> pd.DataFrame:
    """
    获取缓存的DataFrame或重新获取
    
    Args:
        prefix: 缓存前缀
        params: 参数字典
        fetch_func: 获取DataFrame的函数
        use_cache: 是否使用缓存
    
    Returns:
        DataFrame
    """
    if use_cache:
        # 尝试从缓存获取
        cached_df = cache.get_dataframe(prefix, params)
        if cached_df is not None:
            return cached_df
    
    # 重新获取数据
    print(f"🌐 从API获取DataFrame: {prefix}")
    df = fetch_func()
    
    # 存入缓存
    if use_cache and df is not None and not df.empty:
        cache.set_dataframe(prefix, params, df)
    
    return df


if __name__ == "__main__":
    # 测试缓存模块
    print("测试数据缓存模块...")
    
    # 创建测试缓存
    test_cache = DataCache(cache_dir="./test_cache", expire_hours=1)
    
    # 测试数据
    test_data = {
        "symbol": "000300",
        "price": 3500.0,
        "change": 0.5,
        "timestamp": datetime.now().isoformat()
    }
    
    # 写入缓存
    test_cache.set("test_stock", {"symbol": "000300"}, test_data)
    print("✅ 数据已写入缓存")
    
    # 读取缓存
    cached = test_cache.get("test_stock", {"symbol": "000300"})
    if cached:
        print(f"✅ 从缓存读取: {cached}")
    
    # 测试DataFrame缓存
    test_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5),
        "close": [100, 101, 102, 103, 104]
    })
    
    test_cache.set_dataframe("test_df", {"symbol": "000300"}, test_df)
    print("✅ DataFrame已写入缓存")
    
    cached_df = test_cache.get_dataframe("test_df", {"symbol": "000300"})
    if cached_df is not None:
        print(f"✅ 从缓存读取DataFrame:\n{cached_df}")
    
    # 清理测试缓存
    import shutil
    if Path("./test_cache").exists():
        shutil.rmtree("./test_cache")
    
    print("\n测试完成！")
