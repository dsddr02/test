import { connect } from "cloudflare:sockets";

// 配置区块
let 订阅路径 = "test123";
let 我的UUID = "550e8400-e29b-41d4-a716-446655445800";
let 默认节点名称 = "节点";

let 优选TXT = [
  "https://raw.githubusercontent.com/dsddr02/ipupdate/refs/heads/main/valid_ips.txt",
  
];
let 优选列表 = [];

let 反代IP = "ts.hpc.tw:443";

let 启用SOCKS5全局反代 = false;
let SOCKS5账号 = "";

let 伪装网页 = "";

// 网页入口
export default {
  async fetch(访问请求, env) {
    订阅路径 = env.SUB_PATH ?? 订阅路径;
    我的UUID = env.SUB_UUID ?? 我的UUID;
    默认节点名称 = env.SUB_NAME ?? 默认节点名称;
    优选TXT = env.TXT_URL ? 字符串转数组(env.TXT_URL) : 优选TXT;
    反代IP = env.PROXY_IP ?? 反代IP;
    SOCKS5账号 = env.SOCKS5 ?? SOCKS5账号;
    启用SOCKS5全局反代 = env.SOCKS5_GLOBAL === "true";
    伪装网页 = env.FAKE_WEB ?? 伪装网页;

    const 读取我的请求标头 = 访问请求.headers.get("Upgrade");
    const url = new URL(访问请求.url);
    if (!读取我的请求标头 || 读取我的请求标头 !== "websocket") {
      if (优选TXT.length > 0) {
        优选列表 = [
          ...new Set(
            (
              await Promise.all(
                优选TXT.map(async (url) => {
                  const response = await fetch(url);
                  return response.ok
                    ? (await response.text())
                        .split("\n")
                        .map((line) => line.trim())
                        .filter((line) => line)
                    : [];
                })
              )
            ).flat()
          ),
        ];
      }

      const { SOCKS5有效, 反代IP有效 } = 测试SOCKS5和反代IP();
      if (!SOCKS5有效 && !反代IP有效) {
        优选列表.unshift("127.0.0.1#Socks5或反代IP出错，无法访问CF CDN");
      }

      const 最终订阅路径 = encodeURIComponent(订阅路径);
      switch (url.pathname) {
        case `/${最终订阅路径}`:
          const 用户代理 = 访问请求.headers.get("User-Agent").toLowerCase();
          const 配置生成器 = {
            v2ray: v2ray配置文件,
            clash: clash配置文件,
            default: 提示界面,
          };
          const 工具 = Object.keys(配置生成器).find((工具) => 用户代理.includes(工具));
          const 生成配置 = 配置生成器[工具 || "default"];
          return new Response(生成配置(访问请求.headers.get("Host")), {
            status: 200,
            headers: { "Content-Type": "text/plain;charset=utf-8" },
          });
        default:
          if (伪装网页) {
            url.hostname = 伪装网页;
            url.protocol = "https:";
            访问请求 = new Request(url, 访问请求);
            return fetch(访问请求);
          } else {
            return new Response(生成项目介绍页面(),{
              status: 200,
              headers: { "Content-Type": "text/html;charset=utf-8" },});
          }
      }
    } else if (读取我的请求标头 === "websocket") {
      return await 升级WS请求(访问请求);
    }
  },
};
// 脚本主要架构
//第一步，读取和构建基础访问结构
async function 升级WS请求(访问请求) {
  const 创建WS接口 = new WebSocketPair();
  const [客户端, WS接口] = Object.values(创建WS接口);
  WS接口.accept();
  const 读取我的加密访问内容数据头 = 访问请求.headers.get("sec-websocket-protocol");
  const 解密数据 = 使用64位加解密(读取我的加密访问内容数据头); //解密目标访问数据，传递给TCP握手进程
  const { TCP接口, 写入初始数据 } = await 解析VL标头(解密数据); //解析VL数据并进行TCP握手
  建立传输管道(WS接口, TCP接口, 写入初始数据);
  return new Response(null, { status: 101, webSocket: 客户端 });
}
function 使用64位加解密(还原混淆字符) {
  还原混淆字符 = 还原混淆字符.replace(/-/g, "+").replace(/_/g, "/");
  const 解密数据 = atob(还原混淆字符);
  const 解密 = Uint8Array.from(解密数据, (c) => c.charCodeAt(0));
  return 解密.buffer;
}
//第二步，解读VL协议数据，创建TCP握手
async function 解析VL标头(VL数据, TCP接口) {
  if (验证VL的密钥(new Uint8Array(VL数据.slice(1, 17))) !== 我的UUID) {
    return null;
  }
  const 获取数据定位 = new Uint8Array(VL数据)[17];
  const 提取端口索引 = 18 + 获取数据定位 + 1;
  const 建立端口缓存 = VL数据.slice(提取端口索引, 提取端口索引 + 2);
  const 访问端口 = new DataView(建立端口缓存).getUint16(0);
  const 提取地址索引 = 提取端口索引 + 2;
  const 建立地址缓存 = new Uint8Array(VL数据.slice(提取地址索引, 提取地址索引 + 1));
  const 识别地址类型 = 建立地址缓存[0];
  let 地址长度 = 0;
  let 访问地址 = "";
  let 地址信息索引 = 提取地址索引 + 1;
  switch (识别地址类型) {
    case 1:
      地址长度 = 4;
      访问地址 = new Uint8Array(VL数据.slice(地址信息索引, 地址信息索引 + 地址长度)).join(".");
      break;
    case 2:
      地址长度 = new Uint8Array(VL数据.slice(地址信息索引, 地址信息索引 + 1))[0];
      地址信息索引 += 1;
      访问地址 = new TextDecoder().decode(VL数据.slice(地址信息索引, 地址信息索引 + 地址长度));
      break;
    case 3:
      地址长度 = 16;
      const dataView = new DataView(VL数据.slice(地址信息索引, 地址信息索引 + 地址长度));
      const ipv6 = [];
      for (let i = 0; i < 8; i++) {
        ipv6.push(dataView.getUint16(i * 2).toString(16));
      }
      访问地址 = ipv6.join(":");
      break;
  }
  const 写入初始数据 = VL数据.slice(地址信息索引 + 地址长度);
  if (启用SOCKS5全局反代 && SOCKS5账号) {
    TCP接口 = await 创建SOCKS5接口(识别地址类型, 访问地址, 访问端口);
  } else {
    try {
      TCP接口 = await connect({ hostname: 访问地址, port: 访问端口 });
      await TCP接口.opened;
    } catch {
      if (SOCKS5账号) {
        try {
          TCP接口 = await 创建SOCKS5接口(识别地址类型, 访问地址, 访问端口);
          await TCP接口.opened;
        } catch {
          if (反代IP) {
            let [反代IP地址, 反代IP端口] = 反代IP.split(":");
            TCP接口 = await connect({
              hostname: 反代IP地址,
              port: Number(反代IP端口) || 443,
            });
          }
        }
      } else if (反代IP) {
        let [反代IP地址, 反代IP端口] = 反代IP.split(":");
        TCP接口 = await connect({
          hostname: 反代IP地址,
          port: Number(反代IP端口) || 443,
        });
      }
    }
  }
  return { TCP接口, 写入初始数据 };
}
function 验证VL的密钥(arr, offset = 0) {
  const uuid = (
    转换密钥格式[arr[offset + 0]] +
    转换密钥格式[arr[offset + 1]] +
    转换密钥格式[arr[offset + 2]] +
    转换密钥格式[arr[offset + 3]] +
    "-" +
    转换密钥格式[arr[offset + 4]] +
    转换密钥格式[arr[offset + 5]] +
    "-" +
    转换密钥格式[arr[offset + 6]] +
    转换密钥格式[arr[offset + 7]] +
    "-" +
    转换密钥格式[arr[offset + 8]] +
    转换密钥格式[arr[offset + 9]] +
    "-" +
    转换密钥格式[arr[offset + 10]] +
    转换密钥格式[arr[offset + 11]] +
    转换密钥格式[arr[offset + 12]] +
    转换密钥格式[arr[offset + 13]] +
    转换密钥格式[arr[offset + 14]] +
    转换密钥格式[arr[offset + 15]]
  ).toLowerCase();
  return uuid;
}
const 转换密钥格式 = [];
for (let i = 0; i < 256; ++i) {
  转换密钥格式.push((i + 256).toString(16).slice(1));
}
//第三步，创建客户端WS-CF-目标的传输通道并监听状态
async function 建立传输管道(WS接口, TCP接口, 写入初始数据) {
  const 传输数据 = TCP接口.writable.getWriter();
  await WS接口.send(new Uint8Array([0, 0]).buffer); //向客户端发送WS握手认证信息
  TCP接口.readable.pipeTo(
    new WritableStream({
      //将TCP接口返回的数据通过WS接口发送回客户端【优先建立客户端与CF的WS回传通道，防止初始包返回数据时通道任未建立导致丢失数据】
      async write(VL数据) {
        await WS接口.send(VL数据);
      },
    })
  );
  const 数据流 = new ReadableStream({
    //监听WS接口数据并发送给数据流
    async start(控制器) {
      if (写入初始数据) {
        控制器.enqueue(写入初始数据);
        写入初始数据 = null;
      }
      WS接口.addEventListener("message", (event) => {
        控制器.enqueue(event.data);
      }); //监听客户端WS接口消息，推送给数据流
      WS接口.addEventListener("close", () => {
        控制器.close();
      }); //监听客户端WS接口关闭信息，结束流传输
      WS接口.addEventListener("error", () => {
        控制器.close();
      }); //监听客户端WS接口异常信息，结束流传输
    },
  });
  数据流.pipeTo(
    new WritableStream({
      //将客户端接收到的WS数据发往TCP接口
      async write(VL数据) {
        await 传输数据.write(VL数据);
      },
    })
  );
}
// SOCKS5部分
async function 创建SOCKS5接口(识别地址类型, 访问地址, 访问端口) {
  const { username, password, hostname, port } = await 获取SOCKS5账号(SOCKS5账号);
  const SOCKS5接口 = connect({ hostname, port });
  try {
    await SOCKS5接口.opened;
  } catch {
    return new Response("SOCKS5未连通", { status: 400 });
  }
  const writer = SOCKS5接口.writable.getWriter();
  const reader = SOCKS5接口.readable.getReader();
  const encoder = new TextEncoder();
  const socksGreeting = new Uint8Array([5, 2, 0, 2]); //构建认证信息,支持无认证和用户名/密码认证
  await writer.write(socksGreeting);
  let res = (await reader.read()).value;
  if (res[1] === 0x02) {
    //检查是否需要用户名/密码认证
    if (!username || !password) {
      return 关闭接口并退出();
    }
    const authRequest = new Uint8Array([1, username.length, ...encoder.encode(username), password.length, ...encoder.encode(password)]); // 发送用户名/密码认证请求
    await writer.write(authRequest);
    res = (await reader.read()).value;
    if (res[0] !== 0x01 || res[1] !== 0x00) {
      return 关闭接口并退出(); // 认证失败
    }
  }
  let 转换访问地址;
  switch (识别地址类型) {
    case 1: // IPv4
      转换访问地址 = new Uint8Array([1, ...访问地址.split(".").map(Number)]);
      break;
    case 2: // 域名
      转换访问地址 = new Uint8Array([3, 访问地址.length, ...encoder.encode(访问地址)]);
      break;
    case 3: // IPv6
      转换访问地址 = new Uint8Array([4, ...访问地址.split(":").flatMap((x) => [parseInt(x.slice(0, 2), 16), parseInt(x.slice(2), 16)])]);
      break;
    default:
      return 关闭接口并退出();
  }
  const socksRequest = new Uint8Array([5, 1, 0, ...转换访问地址, 访问端口 >> 8, 访问端口 & 0xff]); //发送转换后的访问地址/端口
  await writer.write(socksRequest);
  res = (await reader.read()).value;
  if (res[0] !== 0x05 || res[1] !== 0x00) {
    return 关闭接口并退出(); // 连接失败
  }
  writer.releaseLock();
  reader.releaseLock();
  return SOCKS5接口;
  function 关闭接口并退出() {
    writer.releaseLock();
    reader.releaseLock();
    SOCKS5接口.close();
    return new Response("SOCKS5握手失败", { status: 400 });
  }
}
async function 获取SOCKS5账号(SOCKS5) {
  const [latter, former] = SOCKS5.split("@").reverse();
  let username, password, hostname, port;
  if (former) {
    const formers = former.split(":");
    username = formers[0];
    password = formers[1];
  }
  const latters = latter.split(":");
  port = Number(latters.pop());
  hostname = latters.join(":");
  return { username, password, hostname, port };
}
// 其它
function 字符串转数组(str) {
  return str.split("\n");
}

function 测试SOCKS5和反代IP() {
  let SOCKS5有效 = true;
  let 反代IP有效 = true;

  if (SOCKS5账号) {
    try {
      const { 地址, 端口 } = 获取SOCKS5账号(SOCKS5账号);
      const 测试连接 = connect({ hostname: 地址, port: 端口 });
      测试连接.opened;
      测试连接.close();
    } catch (error) {
      SOCKS5有效 = false;
    }
  } else {
    SOCKS5有效 = false;
  }

  if (反代IP) {
    try {
      const [反代IP地址, 反代IP端口] = 反代IP.split(":");
      const 测试连接 = connect({ hostname: 反代IP地址, port: Number(反代IP端口) || 443 });
      测试连接.opened;
      测试连接.close();
    } catch (error) {
      反代IP有效 = false;
    }
  } else {
    反代IP有效 = false;
  }

  return { SOCKS5有效, 反代IP有效 };
}

function 生成项目介绍页面() {
  return `
<title>项目介绍</title>
<style>
body {
  font-size: 25px;
}
</style>
<pre>
<strong>edge-tunnel</strong>

这是一个基于CF Pages平台的JavaScript,在天书的基础上进行优化
<a href="https://github.com/ImLTHQ/edge-tunnel" target="_blank">点我跳转仓库</a>

不要想着嫖别人订阅啦, 自己部署一个不香吗?

本项目仅供教育、研究和安全测试目的而设计和开发
旨在为安全研究人员、学术界人士及技术爱好者提供一个探索和实践网络通信技术的工具
</pre>
`
}

// 订阅页面
function 提示界面() {
  return `请把链接导入clash或v2ray`;
}

function 处理优选列表(优选列表, hostName) {
  if (优选列表.length === 0) {
    优选列表 = [`${hostName}`];
  }
  return 优选列表.map((获取优选, index) => {
    const [地址端口, 节点名字 = `${默认节点名称} ${index + 1}`] = 获取优选.split("#");
    const 拆分地址端口 = 地址端口.split(":");
    const 端口 = 拆分地址端口.length > 1 ? Number(拆分地址端口.pop()) : 443;
    const 地址 = 拆分地址端口.join(":").replace(/^\[(.+)\]$/, "$1");
    return { 地址, 端口, 节点名字 };
  });
}

function v2ray配置文件(hostName) {
  const 节点列表 = 处理优选列表(优选列表, hostName);
  return 节点列表
    .map(({ 地址, 端口, 节点名字 }) => {
      return `vless://${我的UUID}@${地址}:${端口}?encryption=none&security=tls&sni=${hostName}&fp=chrome&type=ws&host=${hostName}&path=%2F%3Fed%3D2560#${节点名字}`;
    })
    .join("\n");
}

function clash配置文件(hostName) {
  const 节点列表 = 处理优选列表(优选列表, hostName);
  const 生成节点 = (节点列表) => {
    return 节点列表.map(({ 地址, 端口, 节点名字 }) => {
      return {
        nodeConfig: `- name: ${节点名字}
  type: vless
  server: ${地址}
  port: ${端口}
  uuid: ${我的UUID}
  tls: true
  sni: ${hostName}
  network: ws
  ws-opts:
    path: "/?ed=2560"
    headers:
      Host: ${hostName}
      User-Agent: Chrome`,
        proxyConfig: `    - ${节点名字}`,
  udp: true
      };
    });
  };

  const 节点配置 = 生成节点(节点列表)
    .map((node) => node.nodeConfig)
    .join("\n");
  const 代理配置 = 生成节点(节点列表)
    .map((node) => node.proxyConfig)
    .join("\n");

  return `


# 匹配进程 always/strict/off
find-process-mode: strict
global-client-fingerprint: chrome
keep-alive-idle: 600
keep-alive-interval: 30

# 策略组选择和fakeip缓存
profile:
  store-selected: true
  store-fake-ip: true
  
# 流量嗅探
sniffer:
  enable: true
  sniff:
    HTTP:
      ports: [80, 8080-8880]
      override-destination: true
    TLS:
      ports: [443, 8443]
    QUIC:
      ports: [443, 8443]
  force-domain:
    - +.v2ex.com
  skip-domain:
    - "dlg.io.mi.com"
    - "+.push.apple.com"
    - "+.apple.com"
    
# 代理模式
tun:
  enable: true
  stack: mixed
  dns-hijack:
    - "any:53"
    - "tcp://any:53"
  auto-route: true
  auto-redirect: true
  auto-detect-interface: true


proxies:
${节点配置}



proxy-groups:
- name: 🚀 节点选择
  type: select
  proxies:
    - ♻️ 延迟优选
    - 🔯 香港故转
    - 🔯 日本故转
    - ♻️ 香港自动
    - ♻️ 日本自动
    - ♻️ 美国自动
    - ♻️ 自动选择
    - 🇭🇰 香港节点
    - 🇯🇵 日本节点
    - 🇺🇲 美国节点
    - 🌐 全部节点
    - 全球直连

- name: 全球直连
  type: select
  proxies:
    - DIRECT
    

- name: 🎯 CF规则
  type: select
  proxies:
    - 🚀 节点选择
    - DIRECT

- name: 🛑 广告拦截
  type: select
  proxies:
    - REJECT
    - DIRECT
    - 🚀 节点选择

- name: ♻️ 延迟优选
  type: url-test
  url: https://www.google.com/generate_204
  interval: 300
  tolerance: 100
  udp: true
  proxies:
${代理配置}

- name: 📹 YouTube
  type: select
  proxies:
    - 🚀 节点选择

- name: 🍀 Google
  type: select
  proxies:
    - 🚀 节点选择

- name: 🤖 ChatGPT
  type: select
  proxies:
    - 🚀 节点选择

- name: 👨🏿‍💻 GitHub
  type: select
  proxies:
    - 🚀 节点选择

- name: 🐬 OneDrive
  type: select
  proxies:
    - 🚀 节点选择

- name: 🪟 Microsoft
  type: select
  proxies:
    - 🚀 节点选择

- name: 🎵 TikTok
  type: select
  proxies:
    - 🚀 节点选择

- name: 📲 Telegram
  type: select
  proxies:
    - 🚀 节点选择

- name: 🎥 NETFLIX
  type: select
  proxies:
    - 🚀 节点选择

- name: ✈️ Speedtest
  type: select
  proxies:
    - 🚀 节点选择

- name: 💶 PayPal
  type: select
  proxies:
    - 🚀 节点选择

- name: 🍎 Apple
  type: select
  proxies:
    - 全球直连
    - 🚀 节点选择

- name: 🎯 全球直连
  type: select
  proxies:
    - 全球直连
    - 🚀 节点选择

- name: 🐟 漏网之鱼
  type: select
  proxies:
    - 🚀 节点选择

- name: 🇭🇰 香港节点
  type: select
  include-all: true
  filter: "(?i)港|hk|hongkong|hong kong"

- name: 🇯🇵 日本节点
  type: select
  include-all: true
  filter: "(?i)日|jp|japan"

- name: 🇺🇲 美国节点
  type: select
  include-all: true
  filter: "(?i)美|us|unitedstates|united states"

- name: 🔯 香港故转
  type: fallback
  include-all: true
  tolerance: 20
  interval: 300
  filter: "(?=.*(港|HK|(?i)Hong))^((?!(台|日|韩|新|深|美)).)*$"

- name: 🔯 日本故转
  type: fallback
  include-all: true
  tolerance: 20
  interval: 300
  filter: "(?=.*(日|JP|(?i)Japan))^((?!(港|台|韩|新|美)).)*$"

- name: ♻️ 香港自动
  type: url-test
  include-all: true
  tolerance: 20
  interval: 300
  filter: "(?=.*(港|HK|(?i)Hong))^((?!(台|日|韩|新|深|美)).)*$"

- name: ♻️ 日本自动
  type: url-test
  include-all: true
  tolerance: 20
  interval: 300
  filter: "(?=.*(日|JP|(?i)Japan))^((?!(港|台|韩|新|美)).)*$"

- name: ♻️ 美国自动
  type: url-test
  include-all: true
  tolerance: 20
  interval: 300
  filter: "(?=.*(美|US|(?i)States|America))^((?!(港|台|日|韩|新)).)*$"

- name: ♻️ 自动选择
  type: url-test
  include-all: true
  tolerance: 20
  interval: 300
  filter: "^((?!(直连)).)*$"

- name: 🌐 全部节点
  type: select
  include-all: true
rule-anchor:
  ip: &ip {type: http, interval: 86400, behavior: ipcidr, format: mrs}
  domain: &domain {type: http, interval: 86400, behavior: domain, format: mrs}
  class: &class {type: http, interval: 86400, behavior: classical, format: text}
rule-providers:
  reject-domain:
    type: http
    behavior: domain
    url: "https://raw.githubusercontent.com/dsddr02/ipupdate/refs/heads/main/adblock.list"
    format: text
    interval: 86400

  reject-ip:
    type: http
    behavior: ipcidr
    url: "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/ClashRuleSet/reject-ip.list"
    path: ./ruleset/reject-ip.yaml
    interval: 86400
  private_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/private.mrs"}
  proxylite: {!!merge <<: *class, url: "https://raw.githubusercontent.com/qichiyuhub/rule/refs/heads/master/ProxyLite.list"}
  ai: { <<: *domain, url: "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-chat-!cn.mrs" }
  youtube_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/youtube.mrs"}
  google_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/google.mrs"}
  github_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/github.mrs"}
  telegram_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/telegram.mrs"}
  netflix_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/netflix.mrs"}
  paypal_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/paypal.mrs"}
  onedrive_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/onedrive.mrs"}
  microsoft_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/microsoft.mrs"}
  apple_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/apple-cn.mrs"}
  speedtest_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/ookla-speedtest.mrs"}
  tiktok_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/tiktok.mrs"}
  gfw_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/gfw.mrs"}
  geolocation-!cn: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/geolocation-!cn.mrs"}
  cn_domain: {!!merge <<: *domain, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs"}
  
  cn_ip: {!!merge <<: *ip, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/cn.mrs"}
  google_ip: {!!merge <<: *ip, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/google.mrs"}
  telegram_ip: {!!merge <<: *ip, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/telegram.mrs"}
  netflix_ip: {!!merge <<: *ip, url: "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/netflix.mrs"}


rules:
  
  - RULE-SET,reject-domain,🛑 广告拦截
  - RULE-SET,reject-ip,🛑 广告拦截
  - RULE-SET,private_domain,全球直连
  - RULE-SET,apple_domain,🍎 Apple
  - RULE-SET,proxylite,🚀 节点选择
  - RULE-SET,ai,🤖 ChatGPT
  - RULE-SET,github_domain,👨🏿‍💻 GitHub
  - RULE-SET,youtube_domain,📹 YouTube
  - RULE-SET,google_domain,🍀 Google
  - RULE-SET,onedrive_domain,🐬 OneDrive
  - RULE-SET,microsoft_domain,🪟 Microsoft
  - RULE-SET,tiktok_domain,🎵 TikTok
  - RULE-SET,speedtest_domain,✈️ Speedtest
  - RULE-SET,telegram_domain,📲 Telegram
  - RULE-SET,netflix_domain,🎥 NETFLIX
  - RULE-SET,paypal_domain,💶 PayPal
  - RULE-SET,gfw_domain,🚀 节点选择
  - RULE-SET,geolocation-!cn,🚀 节点选择
  - RULE-SET,cn_domain,🎯 全球直连
  - RULE-SET,google_ip,🍀 Google,no-resolve
  - RULE-SET,netflix_ip,🎥 NETFLIX,no-resolve
  - RULE-SET,telegram_ip,📲 Telegram,no-resolve
  - RULE-SET,cn_ip,🎯 全球直连
  - MATCH,🐟 漏网之鱼

`;
}
