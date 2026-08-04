# Third-Party Dependencies

> 项目运行依赖（requirements.lock）的第三方包及许可证清单，用于公开仓库合规审计。
> 生成：脚本解析 requirements.lock × pip-licenses；CI `license` job 自动校验（拦截 UNKNOWN/UNLICENSED）。

| 包 | 版本 | 许可证 |
|----|------|--------|
| alembic | 1.18.5 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.14.2 | MIT |
| brotli | 1.2.0 | MIT |
| charset-normalizer | 3.4.9 | MIT |
| ecdsa | 0.19.2 | MIT |
| fastapi | 0.141.1 | MIT |
| fonttools | 4.63.0 | MIT |
| httptools | 0.8.0 | MIT |
| mypy-extensions | 1.1.0 | MIT |
| pydantic | 2.13.4 | MIT |
| pydantic-core | 2.46.4 | MIT |
| pydantic-settings | 2.14.2 | MIT |
| sqlalchemy | 2.0.51 | MIT |
| typeguard | 4.6.0 | MIT |
| typing-inspection | 0.4.2 | MIT |
| tzlocal | 5.4.4 | MIT |
| urllib3 | 2.7.0 | MIT |
| apscheduler | 3.11.3 | MIT License |
| et-xmlfile | 2.0.0 | MIT License |
| h11 | 0.16.0 | MIT License |
| mako | 1.3.12 | MIT License |
| openpyxl | 3.1.5 | MIT License |
| pandera | 0.32.1 | MIT License |
| pypinyin | 0.55.0 | MIT License |
| python-docx | 1.2.0 | MIT License |
| python-jose | 3.5.0 | MIT License |
| pyyaml | 6.0.3 | MIT License |
| six | 1.17.0 | MIT License |
| tablib | 3.10.0 | MIT License |
| tinyhtml5 | 2.1.0 | MIT License |
| typing-inspect | 0.9.0 | MIT License |
| watchfiles | 1.2.0 | MIT License |
| click | 8.4.2 | BSD-3-Clause |
| idna | 3.18 | BSD-3-Clause |
| lxml | 6.1.1 | BSD-3-Clause |
| markupsafe | 3.0.3 | BSD-3-Clause |
| pycparser | 3.0 | BSD-3-Clause |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| starlette | 1.3.1 | BSD-3-Clause |
| uvicorn | 0.52.1 | BSD-3-Clause |
| websockets | 17.0.1 | BSD-3-Clause |
| cssselect2 | 0.9.0 | BSD License |
| jinja2 | 3.1.6 | BSD License |
| pandas | 3.0.5 | BSD License |
| pydyf | 0.12.1 | BSD License |
| tinycss2 | 1.5.1 | BSD License |
| weasyprint | 69.0 | BSD License |
| webencodings | 0.5.1 | BSD License |
| bcrypt | 5.0.0 | Apache Software License |
| diskcache | 5.6.3 | Apache Software License |
| requests | 2.34.2 | Apache Software License |
| rsa | 4.9.1 | Apache Software License |
| tenacity | 9.1.4 | Apache Software License |
| zopfli | 0.4.3 | Apache Software License |
| msgpack | 1.2.1 | Apache-2.0 |
| pyasn1 | 0.6.4 | BSD-2-Clause |
| pyqt5-sip | 12.18.0 | BSD-2-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| certifi | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) |
| cffi | 2.1.0 | MIT-0 |
| cryptography | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| docxtpl | 0.20.2 | LGPL-2.1-only |
| greenlet | 3.5.4 | MIT AND PSF-2.0 |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| orjson | 3.11.9 | MPL-2.0 AND (Apache-2.0 OR MIT) |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause |
| passlib | 1.7.4 | BSD |
| pillow | 12.3.0 | MIT-CMU |
| prometheus-client | 0.26.0 | Apache-2.0 AND BSD-2-Clause |
| pyphen | 0.17.2 | GNU General Public License v2 or later (GPLv2+); GNU Lesser General Public License v2 or later (LGPLv2+); Mozilla Public License 1.1 (MPL 1.1) |
| pyqt5 | 5.15.11 | GPL v3 |
| pyqt5-qt5 | 5.15.19 | LGPL v3 |
| python-dateutil | 2.9.0.post0 | Apache Software License; BSD License |
| qrcode | 8.2 | BSD License; Other/Proprietary License |
| structlog | 26.1.0 | MIT OR Apache-2.0 |
| typing-extensions | 4.16.0 | PSF-2.0 |
| uvloop | 0.22.1 | Apache Software License; MIT License |

## 合规说明

- **GPL/传染性项**：`pyqt5`(GPLv3+商业双许可)、`pyphen`(GPLv2+/LGPLv2+/MPL1.1)、`docxtpl`(LGPL-2.1-only)。均为桌面端/字体断词库，仅 import 动态链接使用；项目自身许可证选择须在公开发布（M4）前定案（候选：整体 GPLv3 / 换 PySide6(LGPL) / 商业许可）。
- **`qrcode` 8.2**：BSD-3-Clause + 专有双许可元数据（实际为 BSD-3-Clause，可商用）。
- **其余包**：MIT / BSD / Apache / LGPL(Qt) 等，均允许商用。
