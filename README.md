# 家国梦布局计算

## 基本思路

通过模拟人工选择的算法计算

1. 筛选出每个建筑的最高加成列表
2. 从高往低尝试合并列表，取其总系数增长的情况


## 使用方法：

配置文件为 jiaguomeng.yml 内部有详细介绍

```bash
# 参数配置
~ python3 main.py --help
Usage: main.py [OPTIONS]

Options:
  -b, --bomm         Use Explosion Mod.
                     # 爆破模式，非常慢，不做日常使用
  -f, --offline      Offline Mod.
                     # 打开计算离线模式，否则默认计算在线模式
  -o, --only         Only One Building is very important!
                     # 增大首要建筑的系数, 适用于首要建筑超出
                     # 其他建筑等级很多的情况. 造成的效果是选
                     # 择建筑优先考虑加成建筑、而非次要收益建筑
  -c, --config TEXT  Set conf file path.
                     # 设置yml配置文件路径，适用于多人使用
  --help             Show this message and exit.
```


## 备注：
 * 本程序重在优化算法，且带有的爆破模式仅做开发时的结果验证，故未进行高频操作优化。相反故意增大内部结构层级和对象化程度，便于调试算法。
 * 当前与爆破结果尚不完全一致，可能并非最高收益结果，但收益列表已非常清晰，权作参考
 * 原计划后续加入等级配置。老婆表示使用的时候懒得填那么多等级，知道收益系数已足够。故暂不考虑。
 * 待制作需求：
   * 政策填写时需要相加很麻烦，需要一个直接填写当前政策阶段及阶段内4个等级的机制。程序自动计算收益。

## 感谢：
  * 制作时参考了 https://github.com/SQRPI/JiaGuoMeng(@51b31cc09c0a7ffa011d42c23ba1c27dc2c3a8d9) 的爆破逻辑
