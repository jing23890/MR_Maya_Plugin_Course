# 第 11 课：用已做过的 XGen 工具检验你的理解

前十课完成后，再读课程包内的 [XGen 插件源码与启动说明](../scripts/XGenGroomExporter/README.md)。现在插件源码、图标和测试都包含在 scripts/XGenGroomExporter 中，不再依赖工作区外部的插件目录。制作场景和 XGen 缓存仍需你自己提供。

## 先画数据流

```text
UI 收集选项
→ 定位 XGen description
→ 读取样条数据
→ 得到 positions / counts / widths / root UV / group
→ 检查数据契约
→ 写临时 Alembic
→ 验证输出
→ 提交到用户指定路径
```

每个箭头都应该能回答输入是什么、失败会留下什么。读取 XGen 数据和写 Alembic 是不同责任；不能因为导出的头发错位，就马上归咎材质或绑定。

## 数据契约

- counts 表示每根曲线的顶点数；sum(counts) 应等于 positions 中的点数。
- widths 要明确是半径还是直径、单位是什么、按点还是按根存储。不能单凭变量叫 width 就猜测含义。
- root UV 要说明来自哪个头模、哪个 UV 集以及采样方式；UV 不是空间位置，不能无条件用它找任意头模的对应点。
- 位置必须说明坐标空间与单位；同一变换不能在导出和导入两端重复应用。

具体约定以实际 Alembic 写入代码与目标导入规范为准。你的工作是把约定显式记录，并通过一根简单测试曲线验证，而不是只看复杂发型截图猜原因。

## 本课可执行作业：宽度缩放

打开 [练习文件](../exercises/widths_starter.py)。实现 scale_widths：返回新列表；factor 为正有限数；宽度为非负有限数；结果不得溢出；原数据不变。先不用连接 XGen，这样错误容易定位。

在课程根目录运行：

```powershell
$env:COURSE_EXERCISE = 'starter'
& 'C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe' -m unittest discover -s tests -p 'test_widths.py' -v
Remove-Item Env:COURSE_EXERCISE
```

起初会因为 NotImplementedError 失败，这是作业的起点。通过后再看 [参考答案](../exercises/widths_solution.py)，比较验证顺序、输入保护和异常信息。

## 再设计真实集成

在一份工程副本里新增 width_scale 选项：UI 输入 → ExportOptions → 数据转换层 → writer。不要在 UI 里遍历写入 Alembic，也不要永久修改场景中的发丝宽度。缩放只影响 widths，不能把 positions 一起缩放。

集成验收：系数 1 与原输出数据一致；系数 0.5 只改变宽度；非法值在写文件前被拒绝；已有输出在失败后不被破坏；UE 中采用一致材质和灯光比较。这个真实 XGen 集成是留给你的综合任务，课程只提供纯函数参考答案，没有声称已经替你修改生产导出器。

## 文件提交不是 Maya Undo

直接覆盖用户文件后异常退出，会留下损坏结果。更可靠的流程是在目标目录写唯一临时文件，关闭并校验，最后提交；失败清理临时文件。是否覆盖已有文件必须在产品层明确决定。跨磁盘移动、进程崩溃和网络盘都有额外边界，不要把普通 rename 一概当成完整事务。

验收：用自己的话解释头发“粗、位置错、UV 对应失败、材质不对”分别该从哪一层开始排查。

---

[课程首页](../README.md) · [上一课](10-安装发布.md) · [下一课](12-毕业项目.md)
