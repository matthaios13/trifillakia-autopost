/* #34 stickysb2 v3 (16/11): sidebar σε tablet/iPad με native position:sticky (ομαλό, το κάνει ο browser).
   Χωρίς flex: η στήλη παίρνει min-height ίσο με τα άρθρα, overflow:clip αντί hidden μόνο εδώ (και μόνο αν υποστηρίζεται). */
(function(){
var touch=('ontouchstart' in window)||navigator.maxTouchPoints>0||window.__tsstForce;
if(!touch||!(window.CSS&&CSS.supports('overflow','clip')&&CSS.supports('position','sticky')))return;
var st=document.createElement('style');
st.textContent='@media(min-width:768px){html.tsst-on .tn-main-container,html.tsst-on .tn-main-page-wrap{overflow:clip!important}html.tsst-on .tn-sidebar-sticky{position:-webkit-sticky!important;position:sticky!important;top:var(--tsst-top,80px)!important;transform:none!important}}';
document.head.appendChild(st);
document.documentElement.classList.add('tsst-on');
function fit(){[].forEach.call(document.querySelectorAll('.tn-sidebar-sticky'),function(s){var w=s.closest('.tn-sidebar-wrap'),m=w&&w.previousElementSibling;if(!w||!m)return;
 /* μόνο όταν το sidebar είναι δίπλα στο κείμενο, όχι από κάτω */
 if(window.innerWidth<768||Math.abs(w.getBoundingClientRect().top-m.getBoundingClientRect().top)>40){w.style.minHeight='';return}
 w.style.minHeight=m.offsetHeight+'px';
 var h=s.offsetHeight,vh=window.innerHeight;
 /* χωράει στην οθόνη: κολλάει πάνω (80px), αλλιώς κυλάει και κρατιέται στο κάτω μέρος της οθόνης */
 w.style.setProperty('--tsst-top',(h+96<=vh?80:Math.round(vh-h-16))+'px');
 if(window.ResizeObserver&&!w.__tsro){w.__tsro=new ResizeObserver(function(){requestAnimationFrame(fit)});w.__tsro.observe(m);w.__tsro.observe(s)}
})}
if(document.readyState!=='loading')fit();else document.addEventListener('DOMContentLoaded',fit);
window.addEventListener('load',function(){fit();setTimeout(fit,2000)});window.addEventListener('resize',fit);window.addEventListener('orientationchange',function(){setTimeout(fit,300)});
})();
