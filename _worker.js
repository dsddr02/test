import { connect } from "cloudflare:sockets";

// 配置区块
let subscriptionPath = "test";
let identifier = "550e8400-e29b-41d4-a716-446655440060"; // Replaced UUID with identifier
let defaultNodeName = "节点";

let preferredNodes = [];
let TXT_URL_ENV = "";
let preferredTXT = [
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/Domain.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/HKG.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/KHH.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/NRT.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/LAX.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/SEA.txt",
  "https://raw.githubusercontent.com/ImLTHQ/edge-tunnel/main/SJC.txt",
];  // 格式: 地址:端口#节点名称  端口不填默认443 节点名称不填则使用默认节点名称，任何都不填使用自身域名

let outboundAddress = "ts.hpc.tw:443"; // Replaced proxyIP with outboundAddress

let enableSOCKS5GlobalProxy = false;
let SOCKS5Account = "";  // Replaced mySOCKS5Account with SOCKS5Account

// 网页入口
export default {
  async fetch(request, env) {
    subscriptionPath = env.SUB_PATH || subscriptionPath;
    identifier = env.SUB_IDENTIFIER || identifier;  // Replaced SUB_UUID with SUB_IDENTIFIER
    defaultNodeName = env.SUB_NAME || defaultNodeName;
    outboundAddress = env.OUTBOUND_ADDR || outboundAddress;  // Replaced PROXY_IP with OUTBOUND_ADDR
    enableSOCKS5GlobalProxy = env.SOCKS5_GLOBAL === "true" ? true : enableSOCKS5GlobalProxy;
    SOCKS5Account = env.SOCKS5 || SOCKS5Account;

    TXT_URL_ENV = env.TXT_URL;
    if (TXT_URL_ENV) {
      if (typeof TXT_URL_ENV === 'string') {
        preferredTXT = TXT_URL_ENV.split('\n').map(line => line.trim()).filter(line => line);
      } else if (Array.isArray(TXT_URL_ENV)) {
        preferredTXT = TXT_URL_ENV;
      } else {
        preferredTXT = [];
      }
    }

    const readRequestHeader = request.headers.get("Upgrade");
    const url = new URL(request.url);
    if (!readRequestHeader || readRequestHeader !== "websocket") {
      if (preferredTXT.length > 0) {
        preferredNodes = (
          await Promise.all(
            preferredTXT.map((url) =>
              fetch(url).then((response) =>
                response.ok
                  ? response.text().then((text) =>
                      text
                        .split("\n")
                        .map((line) => line.trim())
                        .filter((line) => line)
                    )
                  : []
              )
            )
          )
        ).flat();

        // 去重处理
        preferredNodes = [...new Set(preferredNodes)];
      }

      const encodedSubPath = encodeURIComponent(subscriptionPath);
      if (url.pathname === `/${encodedSubPath}`) {
        const userAgent = request.headers.get("User-Agent").toLowerCase();
        const configGenerator = {
          v2ray: v2rayConfigFile,
          clash: clashConfigFile,
          default: promptPage,
        };
        const tool = Object.keys(configGenerator).find((tool) =>
          userAgent.includes(tool)
        );
        const generateConfig = configGenerator[tool || "default"];
        return new Response(generateConfig(request.headers.get("Host")), {
          status: 200,
          headers: { "Content-Type": "text/plain;charset=utf-8" },
        });
      } else {
        return generateProjectIntroductionPage();
      }
    } else if (readRequestHeader === "websocket") {
      return await upgradeWSRequest(request);
    }
  },
};

// 脚本主要架构
//第一步，读取和构建基础访问结构
async function upgradeWSRequest(request) {
  const createWSInterface = new WebSocketPair();
  const [client, wsInterface] = Object.values(createWSInterface);
  wsInterface.accept();
  const readEncryptedAccessHeader = request.headers.get("sec-websocket-protocol");
  const decryptedData = decryptBase64(readEncryptedAccessHeader); // 解密目标访问数据，传递给TCP握手进程
  const { tcpInterface, writeInitialData } = await parseVLHeader(decryptedData); // 解析VL数据并进行TCP握手
  createTransportPipe(wsInterface, tcpInterface, writeInitialData);
  return new Response(null, { status: 101, webSocket: client });
}

function decryptBase64(obfuscatedString) {
  obfuscatedString = obfuscatedString.replace(/-/g, "+").replace(/_/g, "/");
  const decryptedData = atob(obfuscatedString);
  const decrypted = Uint8Array.from(decryptedData, (c) => c.charCodeAt(0));
  return decrypted.buffer;
}

//第二步，解读VL协议数据，创建TCP握手
async function parseVLHeader(VLData, tcpInterface) {
  if (validateVLKey(new Uint8Array(VLData.slice(1, 17))) !== identifier) { // Replaced UUID with identifier
    return null;
  }
  const dataPosition = new Uint8Array(VLData)[17];
  const extractPortIndex = 18 + dataPosition + 1;
  const portCache = VLData.slice(extractPortIndex, extractPortIndex + 2);
  const accessPort = new DataView(portCache).getUint16(0);
  const extractAddressIndex = extractPortIndex + 2;
  const addressCache = new Uint8Array(VLData.slice(extractAddressIndex, extractAddressIndex + 1));
  const addressType = addressCache[0];
  let addressLength = 0;
  let accessAddress = "";
  let addressInfoIndex = extractAddressIndex + 1;
  switch (addressType) {
    case 1:
      addressLength = 4;
      accessAddress = new Uint8Array(VLData.slice(addressInfoIndex, addressInfoIndex + addressLength)).join(".");
      break;
    case 2:
      addressLength = new Uint8Array(VLData.slice(addressInfoIndex, addressInfoIndex + 1))[0];
      addressInfoIndex += 1;
      accessAddress = new TextDecoder().decode(VLData.slice(addressInfoIndex, addressInfoIndex + addressLength));
      break;
    case 3:
      addressLength = 16;
      const dataView = new DataView(VLData.slice(addressInfoIndex, addressInfoIndex + addressLength));
      const ipv6 = [];
      for (let i = 0; i < 8; i++) {
        ipv6.push(dataView.getUint16(i * 2).toString(16));
      }
      accessAddress = ipv6.join(":");
      break;
  }
  const writeInitialData = VLData.slice(addressInfoIndex + addressLength);
  if (enableSOCKS5GlobalProxy && SOCKS5Account) {
    tcpInterface = await createSOCKS5Interface(addressType, accessAddress, accessPort);
  } else {
    try {
      tcpInterface = connect({ hostname: accessAddress, port: accessPort });
      await tcpInterface.opened;
    } catch {
      if (SOCKS5Account) {
        tcpInterface = await createSOCKS5Interface(addressType, accessAddress, accessPort);
      } else if (outboundAddress) {
        let [outboundAddr, outboundPort] = outboundAddress.split(":");
        tcpInterface = connect({ hostname: outboundAddr, port: outboundPort || accessPort });
      }
    }
  }
  return { tcpInterface, writeInitialData };
}

function validateVLKey(arr, offset = 0) {
  const uuid = (
    convertKeyFormat[arr[offset + 0]] +
    convertKeyFormat[arr[offset + 1]] +
    convertKeyFormat[arr[offset + 2]] +
    convertKeyFormat[arr[offset + 3]] +
    "-" +
    convertKeyFormat[arr[offset + 4]] +
    convertKeyFormat[arr[offset + 5]] +
    "-" +
    convertKeyFormat[arr[offset + 6]] +
    convertKeyFormat[arr[offset + 7]] +
    "-" +
    convertKeyFormat[arr[offset + 8]] +
    convertKeyFormat[arr[offset + 9]] +
    "-" +
    convertKeyFormat[arr[offset + 10]] +
    convertKeyFormat[arr[offset + 11]] +
    convertKeyFormat[arr[offset + 12]] +
    convertKeyFormat[arr[offset + 13]] +
    convertKeyFormat[arr[offset + 14]] +
    convertKeyFormat[arr[offset + 15]]
  ).toLowerCase();
  return uuid;
}

const convertKeyFormat = [];
for (let i = 0; i < 256; ++i) {
  convertKeyFormat.push((i + 256).toString(16).slice(1));
}

//第三步，创建客户端WS-CF-目标的传输通道并监听状态
async function createTransportPipe(wsInterface, tcpInterface, writeInitialData) {
  const transportData = new WritableStream({
    async write(chunk) {
      if (chunk) {
        await tcpInterface.write(chunk);
      }
    },
    async close() {
      await tcpInterface.close();
    },
    abort() {
      tcpInterface.close();
    },
  });

  await transportData.write(writeInitialData); // 推送初始数据
  const pipeToTcp = new ReadableStream({
    async pull(controller) {
      const readBuffer = await tcpInterface.read();
      if (!readBuffer) {
        controller.close();
        return;
      }
      controller.enqueue(readBuffer);
    },
  });

  const pipeToWs = new ReadableStream({
    async pull(controller) {
      const readBuffer = await wsInterface.read();
      if (!readBuffer) {
        controller.close();
        return;
      }
      controller.enqueue(readBuffer);
    },
  });

  const pipeToTcpWriter = pipeToTcp.getWriter();
  const pipeToWsWriter = pipeToWs.getWriter();

  const transportPipe = new WritableStream({
    write(chunk, controller) {
      if (chunk) {
        if (chunk instanceof ArrayBuffer) {
          pipeToTcpWriter.write(chunk);
        } else {
          pipeToWsWriter.write(chunk);
        }
      }
    },
    close() {
      pipeToTcpWriter.close();
      pipeToWsWriter.close();
    },
    abort() {
      pipeToTcpWriter.abort();
      pipeToWsWriter.abort();
    },
  });

  await transportPipe.ready;
}

// 文本生成页面
function generateProjectIntroductionPage() {
  return new Response(`
    <html>
      <head><title>Project</title></head>
      <body>
        <h1>Welcome to the Project!</h1>
        <p>Learn more about this project here.</p>
      </body>
    </html>
  `, { status: 200, headers: { 'Content-Type': 'text/html' } });
}

// 文本生成配置文件
function v2rayConfigFile(host) {
  return `
  {
    "inbounds": [{
      "port": 1080,
      "listen": "0.0.0.0",
      "protocol": "socks",
      "settings": {
        "auth": "noauth",
        "udp": true
      }
    }],
    "outbounds": [{
      "protocol": "vmess",
      "settings": {
        "vnext": [{
          "address": "${host}",
          "port": 443,
          "users": [{
            "id": "${identifier}",
            "alterId": 64,
            "security": "auto"
          }]
        }]
      }
    }]
  }
  `;
}

// clash 配置文件
function clashConfigFile(host) {
  return `
  proxies:
    - name: ${defaultNodeName}
      type: vmess
      server: ${host}
      port: 443
      uuid: ${identifier}
      alterId: 64
      cipher: auto
  proxy-groups:
    - name: default
      type: select
      proxies:
        - ${defaultNodeName}
  rules:
    - DOMAIN-SUFFIX,google.com,default
    - DOMAIN-SUFFIX,github.com,default
    - GEOIP,CN,default
  `;
}

// 简单页面输出
function promptPage(host) {
  return `
    <html>
      <head><title>Config Generation</title></head>
      <body>
        <h1>Configuration generated for ${host}</h1>
      </body>
    </html>
  `;
}
