# 多语言开源方案与验证边界

资料核对日期：2026-11-04。

| 项目 | 用途 | 状态 |
|---|---|---|
| [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | 多语言文本向量，MIT；模型卡称约100语言，低资源语言可能退化 | 已下载权重并完成20语言离线冒烟测试 |
| [Sentence Transformers](https://github.com/huggingface/sentence-transformers) | 加载向量模型 | 可选依赖，独立安装 |
| [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | Apache-2.0，多语言生成与判断 | 通过兼容API适配；未下载或实测该权重 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | 本地推理与兼容HTTP接口 | 已实现兼容聊天适配；协议用本地测试服务验证 |
| [SetFit](https://github.com/huggingface/setfit) | 少样本语义分类训练 | 后续候选，未接入 |

E5不是通用指令模型。描述相似度不能证明逻辑条件成立，否定、复合条件必须单独评测。相似度不等于概率。适配器对超过模型上下文的输入返回待复核，避免静默截断。

```sh
python -m pip install -r requirements-semantic.txt
python semantic.py "Je souhaite un remboursement" examples/labels.json --download
```

首次明确使用 --download 才允许模型下载；之后可离线加载。不要把上游模型语言覆盖声明作为本插件所有语言准确率保证。每种语言应准备独立测试集，报告样本数、接受率、准确率、耗时及设备信息。

标准库模式现在使用Unicode规范化、词和字符特征，可训练更多文字体系，但不具备自动跨语言迁移能力。

MCP安装：`python -m pip install -r requirements-mcp.txt`，设置 DECISIONKIT_CONFIG 为配置文件绝对路径，然后以 `python mcp_server.py` 启动 stdio 服务。旧版 classify 工具还可使用 DECISIONKIT_MODEL 和 DECISIONKIT_DB。不要将服务stdout用于日志。

本项目代码及自制流程图使用MIT许可。开源权重、第三方库仍遵循各自许可证；ZIP不捆绑它们。模型与库版本及下载来源应保留在自己的部署记录中。
