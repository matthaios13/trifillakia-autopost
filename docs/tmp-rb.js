/* #36 radiobtn: διακριτικό κουμπί PAO Radio στο header, ανοίγει μικρό παράθυρο-player για να μη σταματά η μουσική (16/11) */
(function(){
var URL='https://matthaios13.github.io/trifillakia-autopost/player.html';
function run(){
var inner=document.querySelector('.main-nav-inner');if(!inner||document.querySelector('.tsrp'))return;
var css='.tsrp{position:absolute;top:50%;right:58px;z-index:20;transform:translateY(-50%);display:inline-flex;align-items:center;gap:8px;height:34px;padding:0 13px 0 5px;border-radius:999px;background:rgba(0,0,0,.22);border:1px solid rgba(139,212,72,.5);color:#fff!important;font:800 12px Manrope,Arial,sans-serif!important;letter-spacing:.6px;text-decoration:none!important;white-space:nowrap;cursor:pointer;transition:background .2s,border-color .2s}'+
'.tsrp:hover{background:#8BD448;border-color:#8BD448;color:#003a20!important}'+
'.tsrp-ic{position:relative;display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#8BD448}'+
'.tsrp:hover .tsrp-ic{background:#003a20}.tsrp-ic svg{width:12px;height:12px;fill:#003a20;margin-left:2px}.tsrp:hover .tsrp-ic svg{fill:#8BD448}'+
'.tsrp-ic:after{content:"";position:absolute;inset:-3px;border-radius:50%;border:2px solid rgba(139,212,72,.55);animation:tsrpw 2.2s infinite}'+
'@keyframes tsrpw{0%{transform:scale(.9);opacity:1}100%{transform:scale(1.45);opacity:0}}'+
'.tsrp-eq{display:inline-flex;gap:2px;align-items:flex-end;height:12px}.tsrp-eq i{width:2.5px;border-radius:1px;background:#8BD448;animation:tsrpq 1.1s infinite ease-in-out}.tsrp:hover .tsrp-eq i{background:#003a20}'+
'.tsrp-eq i:nth-child(1){height:5px}.tsrp-eq i:nth-child(2){height:11px;animation-delay:.25s}.tsrp-eq i:nth-child(3){height:7px;animation-delay:.5s}'+
'@keyframes tsrpq{0%,100%{transform:scaleY(.45)}50%{transform:scaleY(1)}}.tsrp-eq i{transform-origin:bottom}'+
'.tsrp.mini{padding:0;width:34px;justify-content:center;background:transparent;border-color:transparent}.tsrp.mini .tsrp-tx,.tsrp.mini .tsrp-eq{display:none}'+
'@media(max-width:767px){.tsrp{right:50px}}';
var st=document.createElement('style');st.textContent=css;document.head.appendChild(st);
var a=document.createElement('a');a.className='tsrp';a.href='/radio';a.title='Άκουσε PAO Radio (ανοίγει μικρό παράθυρο, η μουσική δεν σταματάει)';a.setAttribute('aria-label','PAO Radio');
a.innerHTML='<span class="tsrp-ic"><svg viewBox="0 0 24 24"><path d="M7 4.5v15l12.5-7.5z"/><\/svg><\/span><span class="tsrp-tx">PAO RADIO<\/span><span class="tsrp-eq"><i><\/i><i><\/i><i><\/i><\/span>';
a.addEventListener('click',function(ev){ev.preventDefault();
 var w=420,h=700,l=Math.max(0,(screen.availWidth||1200)-w-40),t=60;
 var p=window.open(URL+'?autoplay=1','paoradio','popup=yes,width='+w+',height='+h+',left='+l+',top='+t);
 if(!p)location.href='/radio';else try{p.focus()}catch(_){}});
inner.appendChild(a);
/* αν δεν χωράει δίπλα στο μενού, μένει μόνο το εικονίδιο */
function fit(){a.classList.remove('mini');if(window.innerWidth<768){a.classList.add('mini');return}
 var lis=[].filter.call(inner.querySelectorAll('#menu-main ul.menu > li'),function(li){return li.offsetParent});var last=lis[lis.length-1];
 if(last&&last.getBoundingClientRect().right+14>a.getBoundingClientRect().left)a.classList.add('mini')}
fit();window.addEventListener('resize',fit);window.addEventListener('load',fit);
}
if(document.readyState!=='loading')run();else document.addEventListener('DOMContentLoaded',run);
})();
