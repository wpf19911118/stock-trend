#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合管理模块
跟踪实际持仓、计算收益、管理调仓
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Position:
    """持仓记录"""
    symbol: str
    name: str
    market: str
    shares: float  # 持有份额/股数
    avg_cost: float  # 平均成本
    current_price: float  # 当前价格
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.shares * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """成本"""
        return self.shares * self.avg_cost
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏比例"""
        if self.cost_basis == 0:
            return 0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Transaction:
    """交易记录"""
    date: str
    symbol: str
    name: str
    action: str  # 'buy', 'sell'
    shares: float
    price: float
    amount: float  # 总金额
    fee: float  # 手续费
    reason: str  # 交易原因


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, portfolio_file: str = "./portfolio.json"):
        """
        初始化投资组合管理器
        
        Args:
            portfolio_file: 投资组合文件路径
        """
        self.portfolio_file = Path(portfolio_file)
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
        self.cash: float = 0.0  # 现金余额
        self.initial_capital: float = 0.0  # 初始资金
        
        self._load_portfolio()
    
    def _load_portfolio(self):
        """加载投资组合"""
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.cash = data.get('cash', 0.0)
                self.initial_capital = data.get('initial_capital', 0.0)
                
                # 加载持仓
                for pos_data in data.get('positions', []):
                    pos = Position(**pos_data)
                    self.positions[pos.symbol] = pos
                
                # 加载交易记录
                for trans_data in data.get('transactions', []):
                    trans = Transaction(**trans_data)
                    self.transactions.append(trans)
                
                print(f"✅ 投资组合已加载: {len(self.positions)} 个持仓")
                
            except Exception as e:
                print(f"⚠️ 加载投资组合失败: {e}")
    
    def _save_portfolio(self):
        """保存投资组合"""
        try:
            data = {
                'cash': self.cash,
                'initial_capital': self.initial_capital,
                'updated_at': datetime.now().isoformat(),
                'positions': [asdict(pos) for pos in self.positions.values()],
                'transactions': [asdict(trans) for trans in self.transactions[-100:]]  # 只保留最近100条
            }
            
            with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ 保存投资组合失败: {e}")
    
    def initialize(self, initial_capital: float):
        """
        初始化投资组合
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.transactions = []
        
        self._save_portfolio()
        print(f"✅ 投资组合已初始化: 初始资金 {initial_capital:,.2f} 元")
    
    def buy(self, symbol: str, name: str, market: str, shares: float, 
            price: float, fee_rate: float = 0.0003, reason: str = ""):
        """
        买入
        
        Args:
            symbol: 股票代码
            name: 股票名称
            market: 市场
            shares: 买入数量
            price: 买入价格
            fee_rate: 手续费率（默认万分之3）
            reason: 买入原因
        """
        amount = shares * price
        fee = amount * fee_rate
        total_cost = amount + fee
        
        if total_cost > self.cash:
            print(f"❌ 资金不足: 需要 {total_cost:,.2f}，可用 {self.cash:,.2f}")
            return False
        
        # 更新或创建持仓
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_shares = pos.shares + shares
            total_cost_basis = pos.cost_basis + amount
            pos.shares = total_shares
            pos.avg_cost = total_cost_basis / total_shares
            pos.current_price = price
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                name=name,
                market=market,
                shares=shares,
                avg_cost=price,
                current_price=price
            )
        
        # 扣除现金
        self.cash -= total_cost
        
        # 记录交易
        transaction = Transaction(
            date=datetime.now().strftime('%Y-%m-%d'),
            symbol=symbol,
            name=name,
            action='buy',
            shares=shares,
            price=price,
            amount=amount,
            fee=fee,
            reason=reason
        )
        self.transactions.append(transaction)
        
        self._save_portfolio()
        
        print(f"✅ 买入成功: {name} {shares}股 @ {price:.2f}，手续费 {fee:.2f}")
        return True
    
    def sell(self, symbol: str, shares: Optional[float] = None, 
             price: Optional[float] = None, fee_rate: float = 0.0003, 
             reason: str = ""):
        """
        卖出
        
        Args:
            symbol: 股票代码
            shares: 卖出数量（None表示全部）
            price: 卖出价格（None使用当前价）
            fee_rate: 手续费率
            reason: 卖出原因
        """
        if symbol not in self.positions:
            print(f"❌ 没有持仓: {symbol}")
            return False
        
        pos = self.positions[symbol]
        
        if shares is None:
            shares = pos.shares
        
        if shares > pos.shares:
            print(f"❌ 持仓不足: 持有 {pos.shares}，尝试卖出 {shares}")
            return False
        
        sell_price = price if price else pos.current_price
        amount = shares * sell_price
        fee = amount * fee_rate
        net_amount = amount - fee
        
        # 更新持仓
        pos.shares -= shares
        if pos.shares == 0:
            del self.positions[symbol]
        
        # 增加现金
        self.cash += net_amount
        
        # 记录交易
        transaction = Transaction(
            date=datetime.now().strftime('%Y-%m-%d'),
            symbol=symbol,
            name=pos.name,
            action='sell',
            shares=shares,
            price=sell_price,
            amount=amount,
            fee=fee,
            reason=reason
        )
        self.transactions.append(transaction)
        
        self._save_portfolio()
        
        print(f"✅ 卖出成功: {pos.name} {shares}股 @ {sell_price:.2f}，手续费 {fee:.2f}")
        return True
    
    def update_prices(self, prices: Dict[str, float]):
        """
        更新持仓价格
        
        Args:
            prices: 价格字典 {symbol: price}
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
    
    def rebalance(self, target_allocations: Dict[str, Dict], current_prices: Dict[str, float]):
        """
        调仓
        
        Args:
            target_allocations: 目标配置 {symbol: {'weight': 0.3, 'name': '...', 'market': '...'}}
            current_prices: 当前价格
        """
        print("\n" + "=" * 70)
        print("🔄 开始调仓")
        print("=" * 70)
        
        total_value = self.get_total_value()
        
        for symbol, target in target_allocations.items():
            if symbol not in current_prices:
                continue
            
            target_weight = target['weight']
            target_value = total_value * target_weight
            target_shares = target_value / current_prices[symbol]
            
            current_shares = self.positions[symbol].shares if symbol in self.positions else 0
            
            diff_shares = target_shares - current_shares
            
            if abs(diff_shares) > 100:  # 最小调仓单位
                if diff_shares > 0:
                    # 买入
                    self.buy(
                        symbol=symbol,
                        name=target['name'],
                        market=target['market'],
                        shares=diff_shares,
                        price=current_prices[symbol],
                        reason=f"调仓至目标权重 {target_weight*100:.0f}%"
                    )
                else:
                    # 卖出
                    self.sell(
                        symbol=symbol,
                        shares=abs(diff_shares),
                        price=current_prices[symbol],
                        reason=f"调仓至目标权重 {target_weight*100:.0f}%"
                    )
        
        print("=" * 70)
        self._save_portfolio()
    
    def get_total_value(self) -> float:
        """获取总资产价值"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return positions_value + self.cash
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        total_value = self.get_total_value()
        positions_value = sum(pos.market_value for pos in self.positions.values())
        
        total_return = total_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # 计算已实现盈亏
        realized_pnl = sum([
            trans.amount - trans.fee - (trans.shares * next((t.price for t in self.transactions 
              if t.symbol == trans.symbol and t.action == 'buy' and t.date <= trans.date), trans.price))
            for trans in self.transactions if trans.action == 'sell'
        ])
        
        # 计算未实现盈亏
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'total_value': total_value,
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions_value': positions_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'positions_count': len(self.positions),
            'cash_ratio': self.cash / total_value if total_value > 0 else 0
        }
    
    def get_position_details(self) -> List[Dict]:
        """获取持仓详情"""
        total_value = self.get_total_value()
        
        details = []
        for pos in self.positions.values():
            weight = pos.market_value / total_value if total_value > 0 else 0
            details.append({
                'symbol': pos.symbol,
                'name': pos.name,
                'market': pos.market,
                'shares': pos.shares,
                'avg_cost': pos.avg_cost,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'weight': weight,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct
            })
        
        # 按市值排序
        details.sort(key=lambda x: x['market_value'], reverse=True)
        return details
    
    def get_transactions_history(self, days: int = 30) -> List[Dict]:
        """获取交易历史"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_trans = [
            asdict(trans) for trans in self.transactions
            if datetime.strptime(trans.date, '%Y-%m-%d') >= cutoff_date
        ]
        
        return sorted(recent_trans, key=lambda x: x['date'], reverse=True)
    
    def print_portfolio_report(self):
        """打印投资组合报告"""
        summary = self.get_portfolio_summary()
        positions = self.get_position_details()
        
        print("\n" + "=" * 70)
        print("📊 投资组合报告")
        print("=" * 70)
        
        print(f"\n💰 资产概览:")
        print(f"   总资产: {summary['total_value']:,.2f}")
        print(f"   初始资金: {summary['initial_capital']:,.2f}")
        print(f"   总收益: {summary['total_return']:+,.2f} ({summary['total_return_pct']:+.2f}%)")
        print(f"   已实现盈亏: {summary['realized_pnl']:+,.2f}")
        print(f"   未实现盈亏: {summary['unrealized_pnl']:+,.2f}")
        
        print(f"\n💵 资金分布:")
        print(f"   现金: {summary['cash']:,.2f} ({summary['cash_ratio']*100:.1f}%)")
        print(f"   持仓: {summary['positions_value']:,.2f} ({(1-summary['cash_ratio'])*100:.1f}%)")
        
        if positions:
            print(f"\n📈 持仓详情:")
            for pos in positions:
                emoji = "🟢" if pos['unrealized_pnl'] > 0 else "🔴"
                print(f"   {emoji} {pos['name']} ({pos['symbol']})")
                print(f"      持仓: {pos['shares']:.0f}股 @ 成本{pos['avg_cost']:.2f} 现价{pos['current_price']:.2f}")
                print(f"      市值: {pos['market_value']:,.2f} ({pos['weight']*100:.1f}%)")
                print(f"      盈亏: {pos['unrealized_pnl']:+,.2f} ({pos['unrealized_pnl_pct']:+.2f}%)")
        
        print("\n" + "=" * 70)


def demo_portfolio():
    """演示投资组合管理"""
    print("=" * 70)
    print("💼 投资组合管理演示")
    print("=" * 70)
    
    # 创建管理器
    portfolio = PortfolioManager("./demo_portfolio.json")
    
    # 初始化
    portfolio.initialize(1000000)
    
    # 模拟买入
    print("\n📥 模拟买入...")
    portfolio.buy("000300", "沪深300", "A股", 10000, 3.5, reason="建仓")
    portfolio.buy("^IXIC", "纳斯达克", "美股", 50, 15000, reason="建仓")
    
    # 更新价格
    print("\n📊 更新价格...")
    portfolio.update_prices({
        "000300": 3.8,
        "^IXIC": 15500
    })
    
    # 打印报告
    portfolio.print_portfolio_report()
    
    # 模拟卖出
    print("\n📤 模拟卖出...")
    portfolio.sell("000300", shares=5000, price=3.9, reason="部分获利了结")
    
    # 打印更新后的报告
    portfolio.print_portfolio_report()
    
    print("\n✅ 演示完成!")


if __name__ == "__main__":
    demo_portfolio()
