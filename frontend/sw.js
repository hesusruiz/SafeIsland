if(!self.define){const e=e=>{"require"!==e&&(e+=".js");let s=Promise.resolve();return i[e]||(s=new Promise((async s=>{if("document"in self){const i=document.createElement("script");i.src=e,document.head.appendChild(i),i.onload=s}else importScripts(e),s()}))),s.then((()=>{if(!i[e])throw new Error(`Module ${e} didn’t register its module`);return i[e]}))},s=(s,i)=>{Promise.all(s.map(e)).then((e=>i(1===e.length?e[0]:e)))},i={require:Promise.resolve(s)};self.define=(s,r,c)=>{i[s]||(i[s]=Promise.resolve().then((()=>{let i={};const a={uri:location.origin+s.slice(1)};return Promise.all(r.map((s=>{switch(s){case"exports":return i;case"module":return a;default:return e(s)}}))).then((e=>{const s=c(...e);return i.default||(i.default=s),i}))})))}}define("./sw.js",["./workbox-7a19dc20"],(function(e){"use strict";self.skipWaiting(),e.clientsClaim(),e.precacheAndRoute([{url:"__target__/hola.js",revision:"9192d21aa0f2afde716458d747f3c015"},{url:"__target__/org.transcrypt.__runtime__.js",revision:"c296bd321e3ed911f9a4d5e97eae90b9"},{url:"creds/SafeIslandCovidTestResult.json",revision:"4ac0f8cf619a98d42745f37cfef0097b"},{url:"css/all.css",revision:"4555eb8b3aa10c9ad9b6db95a12ac460"},{url:"css/mystyles.css",revision:"b9f8cb94dbdef03f961a358df415ebc2"},{url:"css/prism.css",revision:"15f346572a9f57e0441d684ee79aed0e"},{url:"css/safeisland.css",revision:"a1047b18173c8cb23c894cc5232d8105"},{url:"css/safeisland2.css",revision:"47eb16b1a8a3a635a37e8acd655d2e2a"},{url:"css/solid.css",revision:"8cae1a02b3d90201b38e8e0aa5aef4eb"},{url:"favicon.ico",revision:"6f108e13cd2eb50eae504ae4a7fcbe6b"},{url:"img/bg-hero-sello.png",revision:"c19536b095b22cba914732653a9af2ec"},{url:"img/bg-hero.png",revision:"54e781dc6e0bda84b6f8621ce6df7633"},{url:"img/icon-120.png",revision:"265f57479cc3afd9cbbfd6309c27d874"},{url:"img/icon-152.png",revision:"5232689bce3ec2aaf1411d392514e108"},{url:"img/icon-180.png",revision:"a8aa1377d0d5bc86c0a89530f5eb7dc3"},{url:"img/icon-192.png",revision:"b2d05de40b0301caf59a21535a9a9e8c"},{url:"img/icon-32.png",revision:"5cfca066e467bf792e7ac278465d2e99"},{url:"img/icon-512.png",revision:"28cc36e33d9a447fe36c938433b8a0f7"},{url:"img/icon-76.png",revision:"cc8d137440d19acfbb43a29990453b36"},{url:"img/icon.png",revision:"ab5efd94a87ea215d48a2aa311a6eb25"},{url:"img/Logo.png",revision:"36bb60037069cb6185dcdb25fa91ba8c"},{url:"index.html",revision:"d547d7bed97f2491ed9460f1d9db6710"},{url:"js/app.js",revision:"70b626c050b743a1fab4efed0ac870e5"},{url:"js/easy.qrcode.min.js",revision:"64a13f2e8068f8636735233731c138b0"},{url:"js/install.js",revision:"f54508a714e097f8a3dc02005fe27cf0"},{url:"js/jquery-3.5.1.min.js",revision:"dc5e7f18c8d36ac1d3d4753a87c98d0a"},{url:"js/jsQR.js",revision:"06c4d5a0dd8975a781f089e8b308e5b8"},{url:"js/localforage.min.js",revision:"f546207fcb7089d58b75b3ef57f37bf6"},{url:"js/prism.js",revision:"7509ebc811e64bce49ac728962592ada"},{url:"manifest.json",revision:"99beb1f718406e215b82ecbbcc09fa70"},{url:"onsen.html",revision:"081473a957f5216e72c3f5a478e41383"},{url:"passenger.html",revision:"05e1ab626ef55116c7f148803c66987d"},{url:"sw-in.js",revision:"5535bb7f42a0a2c0e97adb2ae8e62a7d"}],{})}));
//# sourceMappingURL=sw.js.map
