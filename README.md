# Douyin Creator Knowledge Base

把一个抖音博主的全部作品做成结构化知识库的 skill。

## 流程

1. 收齐作品清单（序号、标题、链接，含图文）
2. TikVid 下载音频（免登录）
3. faster-whisper 转录成文字
4. 提炼成知识库：概况、主题索引、逐支摘要、缺失清单
5. 需要时再做专题分析

## 文件

- `SKILL.md`：完整方法
- `skill.yaml`：skill 描述
- `scripts/tikvid_batch.py`：批量下载音频
- `scripts/transcribe.py`：批量转录

## 使用

在 Muse 里通过 skill 调用；新项目先改两个脚本顶部的路径常量。

## 注意

- 默认只看不互动（不点赞、不评论、不关注、不私信）
- TikVid 方法 2026 年 10 月实测可用，平台规则可能变化
- 转录稿是无标点 ASR 文本，仅作个人学习记录
