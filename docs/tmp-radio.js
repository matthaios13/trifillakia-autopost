/* #35 radio: σελίδα /radio, πρόγραμμα PAO Radio (docs/radio.json του bot) + player (16/11) */
(function(){
function run(){
var box=document.querySelector('.tsrd');if(!box||box.dataset.on)return;box.dataset.on=1;
var SRC='https://raw.githubusercontent.com/matthaios13/trifillakia-autopost/main/docs/radio.json';
var TZ='Europe/Athens',DN=['Κυριακή','Δευτέρα','Τρίτη','Τετάρτη','Πέμπτη','Παρασκευή','Σάββατο'];
var css='.tsrd [hidden]{display:none!important}.tsrd{font-family:Manrope,Arial,sans-serif;color:#fff;margin:0 0 30px}.tsrd *{box-sizing:border-box}'+
'.page-content-wrap:has(.tsrd){background:transparent!important;padding:0!important}'+
'.tsrd-hero{position:relative;overflow:hidden;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:26px;align-items:center;padding:28px;border-radius:22px;background:radial-gradient(circle at 90% 10%,rgba(139,212,72,.3),transparent 45%),linear-gradient(140deg,#006b3d,#003a20 70%);border:1px solid rgba(139,212,72,.35)}'+
'.tsrd-media{position:relative;border-radius:16px;overflow:hidden;background:#002414;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center}'+
'.tsrd-media iframe{position:absolute;inset:0;width:100%;height:100%;border:0}'+
'.tsrd-art{position:absolute;inset:0;background:url(https://paoradio.gr/wp-content/uploads/2023/11/PAO_Radio-01.png) center/38% no-repeat,radial-gradient(circle,#0b5a33,#002414 70%);opacity:.9}'+
'.tsrd-play{position:relative;z-index:1;width:84px;height:84px;border-radius:50%;border:0;background:#8BD448;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 10px rgba(139,212,72,.18),0 10px 30px rgba(0,0,0,.35);transition:transform .2s}'+
'.tsrd-play:hover{transform:scale(1.06)}.tsrd-play svg{width:34px;height:34px;fill:#003a20}'+
'.tsrd-eq{position:absolute;left:16px;bottom:14px;display:none;gap:3px;align-items:flex-end;height:22px}.tsrd.playing .tsrd-eq{display:flex}.tsrd-eq i{width:4px;background:#8BD448;border-radius:2px;animation:tsrdq 1s infinite ease-in-out}.tsrd-eq i:nth-child(2){animation-delay:.2s}.tsrd-eq i:nth-child(3){animation-delay:.4s}.tsrd-eq i:nth-child(4){animation-delay:.6s}'+
'@keyframes tsrdq{0%,100%{height:5px}50%{height:22px}}'+
'.tsrd-kick{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;background:rgba(139,212,72,.16);border:1px solid rgba(139,212,72,.45);color:#8BD448;font:900 11.5px Manrope,Arial,sans-serif;letter-spacing:1.2px}'+
'.tsrd-kick i{width:8px;height:8px;border-radius:50%;background:#ff3355;box-shadow:0 0 0 0 rgba(255,51,85,.6);animation:tsrdp 1.6s infinite}@keyframes tsrdp{70%{box-shadow:0 0 0 8px rgba(255,51,85,0)}}'+
'.tsrd h2.tsrd-now{margin:14px 0 6px!important;color:#fff!important;font:900 30px/1.15 Manrope,Arial,sans-serif!important}'+
'.tsrd-topic{margin:0 0 14px!important;color:rgba(255,255,255,.82)!important;font:600 15.5px/1.5 Manrope,Arial,sans-serif!important}'+
'.tsrd-time{display:flex;align-items:center;gap:10px;color:rgba(255,255,255,.75);font:800 13px Manrope,Arial,sans-serif}.tsrd-bar{flex:1;height:6px;border-radius:999px;background:rgba(255,255,255,.15);overflow:hidden}.tsrd-bar b{display:block;height:100%;background:linear-gradient(90deg,#60AD5E,#8BD448)}'+
'.tsrd-next{margin-top:16px;padding:12px 14px;border-radius:14px;background:rgba(0,0,0,.22);border:1px solid rgba(139,212,72,.25);font:700 14px/1.4 Manrope,Arial,sans-serif}.tsrd-next small{display:block;color:#8BD448;font:900 11px Manrope,Arial,sans-serif;letter-spacing:1px;margin-bottom:3px}'+
'.tsrd-vol{display:flex;align-items:center;gap:10px;margin-top:14px;color:rgba(255,255,255,.75);font:800 12px Manrope,Arial,sans-serif}.tsrd-vol input{flex:1;max-width:200px;accent-color:#8BD448}'+
'.tsrd h3.tsrd-h{margin:30px 0 12px!important;color:#fff!important;font:900 24px Manrope,Arial,sans-serif!important}'+
'.tsrd-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.tsrd-tab{padding:9px 16px;border-radius:999px;border:1.5px solid rgba(139,212,72,.4);background:transparent;color:#fff;font:800 13px Manrope,Arial,sans-serif;cursor:pointer}.tsrd-tab.on{background:#8BD448;color:#003a20;border-color:#8BD448}'+
'.tsrd-list{display:flex;flex-direction:column;gap:8px}'+
'.tsrd-row{display:grid;grid-template-columns:110px 1fr auto;gap:14px;align-items:center;padding:14px 16px;border-radius:14px;background:linear-gradient(150deg,#005833,#003a20 80%);border:1px solid rgba(139,212,72,.2)}'+
'.tsrd-row.past{opacity:.5}.tsrd-row.now{border-color:#8BD448;box-shadow:0 0 0 2px rgba(139,212,72,.35)}.tsrd-row.music{background:rgba(0,30,15,.5);padding:10px 16px}'+
'.tsrd-row .t{color:#8BD448;font:900 15px Manrope,Arial,sans-serif}.tsrd-row .t small{display:block;color:rgba(255,255,255,.55);font:700 11.5px Manrope,Arial,sans-serif}'+
'.tsrd-row .s b{display:block;color:#fff;font:900 15px/1.3 Manrope,Arial,sans-serif}.tsrd-row .s span{display:block;margin-top:2px;color:rgba(255,255,255,.75);font:600 13.5px/1.45 Manrope,Arial,sans-serif}'+
'.tsrd-b{padding:4px 9px;border-radius:7px;font:900 10.5px Manrope,Arial,sans-serif;letter-spacing:.8px;white-space:nowrap;background:rgba(255,255,255,.1);color:rgba(255,255,255,.8)}.tsrd-b.live{background:#ff3355;color:#fff}.tsrd-b.nw{background:#8BD448;color:#003a20}'+
'.tsrd-foot{margin-top:20px;text-align:center;color:rgba(255,255,255,.7);font:600 13.5px Manrope,Arial,sans-serif}.tsrd-foot a{color:#8BD448!important;font-weight:800;text-decoration:none!important}'+
'@media(max-width:767px){.tsrd-hero{grid-template-columns:1fr;padding:18px;gap:16px}.tsrd h2.tsrd-now{font-size:23px!important}.tsrd-row{grid-template-columns:72px 1fr;gap:10px}.tsrd-row .tsrd-b{grid-column:2;justify-self:start}}';
var stl=document.createElement('style');stl.textContent=css;document.head.appendChild(stl);
function e(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function hm(ts){return new Date(ts*1000).toLocaleTimeString('el-GR',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:TZ})}
function dkey(ts){return new Date(ts*1000).toLocaleDateString('en-CA',{timeZone:TZ})}
function dname(ts){var k=dkey(ts),now=Date.now()/1000;if(k===dkey(now))return 'Σήμερα';if(k===dkey(now+86400))return 'Αύριο';var d=new Date(ts*1000);return DN[new Date(d.toLocaleString('en-US',{timeZone:TZ})).getDay()]+' '+d.toLocaleDateString('el-GR',{day:'numeric',month:'numeric',timeZone:TZ})}
var PLAY='<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z"/><\/svg>',STOP='<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/><\/svg>';
var data=null,audio=null,curKey='',songT=0;
box.innerHTML='<div class="tsrd-hero"><div class="tsrd-media" id="tsrdM"><\/div><div><span class="tsrd-kick"><i><\/i>PAO RADIO · ΣΤΟΝ ΑΕΡΑ<\/span><h2 class="tsrd-now" id="tsrdN">…<\/h2><p class="tsrd-topic" id="tsrdT"><\/p><div class="tsrd-time"><span id="tsrdA"><\/span><span class="tsrd-bar"><b id="tsrdP"><\/b><\/span><span id="tsrdB"><\/span><\/div><div class="tsrd-vol" id="tsrdV" hidden><span>Ένταση<\/span><input type="range" min="0" max="100" value="80" aria-label="Ένταση"><\/div><div class="tsrd-next" id="tsrdX" hidden><\/div><\/div><\/div><h3 class="tsrd-h">Πρόγραμμα<\/h3><div class="tsrd-tabs" id="tsrdD"><\/div><div class="tsrd-list" id="tsrdL"><\/div><div class="tsrd-foot">Το PAO Radio παίζει 24/7 και στο <a href="https://paoradio.gr/" target="_blank" rel="noopener">paoradio.gr<\/a><\/div>';
var $=function(id){return document.getElementById(id)};
$('tsrdV').querySelector('input').addEventListener('input',function(){if(audio)audio.volume=this.value/100});
function current(){var now=Date.now()/1000;return (data.rows||[]).filter(function(r){return r[0]<=now&&now<r[1]})[0]||null}
function nextShow(){var now=Date.now()/1000;return (data.rows||[]).filter(function(r){return r[0]>now&&r[4]!=='music'})[0]||null}
function song(){if(!data||!data.status||Date.now()-songT<15000)return;songT=Date.now();fetch(data.status).then(function(r){return r.json()}).then(function(j){var s=j&&j.icestats&&j.icestats.source;if(s&&s.length)s=s[0];var t=s?(s.yp_currently_playing||[s.artist,s.title].filter(Boolean).join(' – ')):'';var c=current();if(t&&(!c||c[4]==='music'))$('tsrdT').textContent='♫ '+t}).catch(function(){})}
function toggle(){var b=box.querySelector('.tsrd-play');if(audio&&!audio.paused){audio.pause();box.classList.remove('playing');if(b)b.innerHTML=PLAY;return}
 if(!audio){audio=new Audio(data.stream);audio.preload='none';audio.volume=$('tsrdV').querySelector('input').value/100}
 audio.src=data.stream+'?t='+Date.now();audio.play().then(function(){box.classList.add('playing');if(b)b.innerHTML=STOP}).catch(function(){})}
function hero(){var c=current(),now=Date.now()/1000;
 var key=c?(c[0]+'|'+c[4]):'none';
 if(key!==curKey){curKey=key;var m=$('tsrdM');
  if(c&&c[4]!=='music'&&c[5]){if(audio){audio.pause();box.classList.remove('playing')}
   var st=c[4]==='live'?0:Math.max(0,Math.floor(now-c[0]));
   m.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+e(c[5])+'?rel=0&playsinline=1&start='+st+'" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen title="'+e(c[2])+'"><\/iframe>';$('tsrdV').hidden=true}
  else{m.innerHTML='<span class="tsrd-art"><\/span><button type="button" class="tsrd-play" aria-label="Άκουσε PAO Radio">'+(audio&&!audio.paused?STOP:PLAY)+'<\/button><span class="tsrd-eq"><i><\/i><i><\/i><i><\/i><i><\/i><\/span>';m.querySelector('.tsrd-play').addEventListener('click',toggle);$('tsrdV').hidden=false}
  $('tsrdN').textContent=c?(c[4]==='music'?'Μουσική στο PAO Radio':c[2]):'PAO Radio';
  $('tsrdT').textContent=c?(c[4]==='music'?'Non stop μουσική':(c[4]==='rerun'?'Επανάληψη · ':'')+c[3]):'';
  songT=0}
 if(c){$('tsrdA').textContent=hm(c[0]);$('tsrdB').textContent=hm(c[1]);$('tsrdP').style.width=Math.min(100,(now-c[0])/(c[1]-c[0])*100)+'%'}
 var n=nextShow(),x=$('tsrdX');if(n){x.hidden=false;x.innerHTML='<small>ΑΚΟΛΟΥΘΕΙ · '+e(dname(n[0]))+' '+hm(n[0])+'<\/small>'+e(n[2])+(n[3]?' – '+e(n[3]):'')}else x.hidden=true;
 if(c&&c[4]==='music')song()}
var day='';
function list(){var now=Date.now()/1000,days=[],by={};(data.rows||[]).forEach(function(r){if(r[1]<now-3600*3&&dkey(r[0])!==dkey(now))return;var k=dkey(r[0]);if(!by[k]){by[k]=[];days.push(k)}by[k].push(r)});
 if(!day||!by[day])day=days[0];var t=$('tsrdD');t.innerHTML='';days.forEach(function(k){var b=document.createElement('button');b.type='button';b.className='tsrd-tab'+(k===day?' on':'');b.textContent=dname(by[k][0][0]);b.addEventListener('click',function(){day=k;list()});t.appendChild(b)});
 $('tsrdL').innerHTML=(by[day]||[]).map(function(r){var cls='tsrd-row'+(r[4]==='music'?' music':'')+(r[1]<=now?' past':'')+(r[0]<=now&&now<r[1]?' now':'');
  var badge=r[0]<=now&&now<r[1]?'<span class="tsrd-b nw">ΤΩΡΑ<\/span>':r[4]==='live'?'<span class="tsrd-b live">LIVE<\/span>':r[4]==='rerun'?'<span class="tsrd-b">ΕΠΑΝΑΛΗΨΗ<\/span>':'<span class="tsrd-b">ΜΟΥΣΙΚΗ<\/span>';
  return '<div class="'+cls+'"><div class="t">'+hm(r[0])+'<small>έως '+hm(r[1])+'<\/small><\/div><div class="s"><b>'+e(r[4]==='music'?'Μουσική':r[2])+'<\/b>'+(r[4]==='music'?'':'<span>'+e(r[3])+'<\/span>')+'<\/div>'+badge+'<\/div>'}).join('')}
function load(){fetch(SRC+'?t='+Math.floor(Date.now()/300000)).then(function(r){return r.json()}).then(function(d){data=d;hero();list()}).catch(function(){$('tsrdN').textContent='Το πρόγραμμα δεν είναι διαθέσιμο αυτή τη στιγμή'})}
load();setInterval(function(){if(data){hero();if(new Date().getSeconds()<10)list()}},10000);setInterval(load,600000);
}
if(document.readyState!=='loading')run();else document.addEventListener('DOMContentLoaded',run);
})();
