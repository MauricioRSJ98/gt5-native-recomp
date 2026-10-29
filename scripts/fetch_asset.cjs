// Download pinned tools locally; follow only HTTPS redirects on known vendors.
const https=require('node:https'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const project=path.resolve(__dirname,'..');
const [url,destination,expected]=process.argv.slice(2);
const dest=path.resolve(destination);
if(!dest.startsWith(project+path.sep))throw Error('Destination must be inside project');
const allowed=new Set(['github.com','api.github.com','codeload.github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','nodejs.org','registry.npmjs.org']);
function fetch(address,redirects=0){
 const u=new URL(address);
 if(u.protocol!=='https:'||!allowed.has(u.hostname)||redirects>6)throw Error('Unapproved redirect');
 https.get(u,{headers:{'User-Agent':'GT5-native-tools'}},res=>{
  if(res.statusCode>=300&&res.statusCode<400){res.resume();return fetch(new URL(res.headers.location,u).href,redirects+1);}
  if(res.statusCode!==200){res.resume();console.error('HTTP',res.statusCode);process.exitCode=1;return;}
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  const stream=fs.createWriteStream(dest,{flags:'wx'}),hash=crypto.createHash('sha256');let bytes=0;
  res.on('data',b=>{hash.update(b);bytes+=b.length;});res.pipe(stream);
  stream.on('finish',()=>{const sha=hash.digest('hex');if(expected&&sha!==expected){console.error('SHA256 MISMATCH');process.exitCode=1;}else console.log(JSON.stringify({file:dest,bytes,sha256:sha}));});
  stream.on('error',e=>{console.error(e.message);res.destroy();process.exitCode=1;});
 }).on('error',e=>{console.error(e.message);process.exitCode=1;});
}
fetch(url);
