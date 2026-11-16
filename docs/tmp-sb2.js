/* #34 stickysb2: το sidebar ακολουθεί το scroll σε tablet/iPad (μόνο transform, καμία αλλαγή στο layout)
   v2 (16/11): όσο γίνεται scroll δεν κουνιέται (στο iPad έτρεμε/θόλωνε), γλιστράει ομαλά στη θέση του μόλις σταματήσει */
(function(){
var touch=('ontouchstart' in window)||navigator.maxTouchPoints>0||window.__tsstForce;
if(!touch)return;
var items=[],timer=0;
function collect(){items.forEach(function(o){var w=o.s.closest('.tn-sidebar-wrap');if(w){w.style.transition='';w.style.transform=''}});items=[].map.call(document.querySelectorAll('.tn-sidebar-sticky'),function(s){return{s:s,t:0}})}
function upd(anim){var y=window.pageYOffset,vh=window.innerHeight;
 items.forEach(function(o){var s=o.s,w=s.closest('.tn-sidebar-wrap'),row=w&&w.parentElement;if(!row)return;
  /* μόνο όταν το sidebar είναι δίπλα στο κείμενο (≥768), όχι από κάτω */
  var rr=row.getBoundingClientRect(),wr=w.getBoundingClientRect(),m=w.previousElementSibling,mr=m?m.getBoundingClientRect():rr;
  var cur=new DOMMatrix(getComputedStyle(w).transform).m42||0;
  if(window.innerWidth<768||Math.abs(wr.top-cur-mr.top)>40||wr.left<mr.left+100){if(o.t){o.t=0;w.style.transition='';w.style.transform=''}return}
  var sh=w.offsetHeight,base=wr.top+y-cur,end=rr.top+y+row.offsetHeight;
  var max=Math.max(0,end-(base+sh)),t;
  if(sh+96<=vh)t=y+80-base;            /* χωράει στην οθόνη: κολλάει από πάνω */
  else t=y+vh-16-(base+sh);            /* ψηλό: κυλάει και κρατιέται στο κάτω μέρος της οθόνης */
  t=Math.round(Math.max(0,Math.min(max,t)));
  if(t!==o.t){o.t=t;w.style.transition=anim?'transform .45s cubic-bezier(.2,.7,.2,1)':'';w.style.transform=t?'translateY('+t+'px)':''}
 })}
function onScroll(){clearTimeout(timer);timer=setTimeout(function(){upd(true)},140)}
function go(){collect();upd(false)}
if(document.readyState!=='loading')go();else document.addEventListener('DOMContentLoaded',go);
window.addEventListener('load',function(){go();setTimeout(go,2000)});
window.addEventListener('scroll',onScroll,{passive:true});window.addEventListener('resize',function(){upd(false)});window.addEventListener('orientationchange',function(){setTimeout(function(){upd(false)},300)});
})();
