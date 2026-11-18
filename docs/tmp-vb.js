/* #37 vibercta: «Κάντε εγγραφή στο κανάλι μας στο Viber» στο τέλος κάθε άρθρου/blog (18/11) */
(function(){
var URL='https://invite.viber.com/?g2=AQABUt3RNlxlkE%2BnKPqUk87IFDRCAwbpgFFyTJvyy93ilbJ987ot3fETxIENjO1D';
function run(){
var body=document.querySelector('.node-article .field-name-body, .node-blog .field-name-body, .post-content-wrap .field-name-body');
if(!body||document.querySelector('.tsvb'))return;
var css='.tsvb{display:flex;align-items:center;gap:16px;margin:26px 0 8px;padding:16px 18px;border-radius:16px;background:linear-gradient(135deg,#7360F2,#59267C);color:#fff;font-family:Manrope,Arial,sans-serif;text-decoration:none!important;box-shadow:0 10px 26px rgba(89,38,124,.25);transition:transform .2s}'+
'.tsvb:hover{transform:translateY(-2px)}'+
'.tsvb-ic{flex:0 0 46px;width:46px;height:46px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center}'+
'.tsvb-ic svg{width:26px;height:26px;fill:#7360F2}'+
'.tsvb-tx{flex:1;min-width:0;color:#fff!important;font:700 15px/1.45 Manrope,Arial,sans-serif}'+
'.tsvb-tx b{display:block;margin-bottom:2px;color:#fff!important;font:900 16px Manrope,Arial,sans-serif}'+
'.tsvb-bt{flex:0 0 auto;padding:10px 16px;border-radius:999px;background:#fff;color:#59267C!important;font:900 13px Manrope,Arial,sans-serif;letter-spacing:.4px;white-space:nowrap}'+
'.post-content-wrap .field-name-body a.tsvb,.post-content-wrap .field-name-body a.tsvb:hover{background-image:linear-gradient(135deg,#7360F2,#59267C)!important;background-color:transparent!important;color:#fff!important;padding:16px 18px!important;border-radius:16px!important}'+
'@media(max-width:600px){.tsvb{flex-wrap:wrap;gap:12px;padding:14px!important}.tsvb-tx{flex:1 1 calc(100% - 62px);font-size:14px}.tsvb-bt{flex:1 1 100%;text-align:center}}';
var st=document.createElement('style');st.textContent=css;document.head.appendChild(st);
var a=document.createElement('a');a.className='tsvb';a.href=URL;a.target='_blank';a.rel='noopener';
a.innerHTML='<span class="tsvb-ic"><svg viewBox="0 0 24 24"><path d="M11.4 1C6.9 1.1 2.2 2.3 1.6 8.5c-.3 3.1-.2 5.9.6 8.3.7 2 2 3.4 4 4.1v2.6c0 .5.6.7.9.4l2.6-2.8c.9.1 1.8.1 2.7 0 4.5-.4 7.9-2 9.3-5.7.9-2.4.9-5.9.1-8.2C20.5 2.4 15.9 1 11.4 1zm.2 2c3.9 0 7.4 1.1 8.3 3.9.7 2 .7 5 0 7-1 2.7-3.7 3.9-7.5 4.2-.9.1-1.9.1-2.8 0l-.4-.1-2 2.1v-2.3l-.4-.1c-1.7-.5-2.8-1.6-3.3-3.2-.7-2.1-.8-4.6-.5-7.4C3.4 3.4 7.2 3.1 11.6 3zm.1 2.2c-.3 0-.3.4 0 .5 2.4.1 4.2 1.8 4.3 4.3 0 .3.5.3.5 0 0-2.7-2-4.8-4.8-4.8zm-3.5.5c-.5 0-1.2.6-1.4 1.1-.3.7-.1 1.4.4 2.3 1.1 1.9 2.6 3.5 4.6 4.6.8.4 1.4.7 2 .5.5-.2 1.2-.9 1.3-1.4.1-.4-.2-.6-.5-.8l-1.4-1c-.4-.2-.8-.1-1 .2l-.4.6c-.2.3-.5.2-.5.2-1.5-.6-2.5-1.6-3.1-3.1 0 0-.1-.3.2-.5l.6-.4c.3-.2.4-.6.2-1l-1-1.4c-.2-.2-.4-.3-.6-.3zm3.6.7c-.3 0-.3.4 0 .5 1.3.1 2.1.9 2.2 2.2 0 .3.5.3.5 0-.1-1.5-1.2-2.7-2.7-2.7zm.2 1.3c-.3 0-.3.4 0 .5.5 0 .8.3.8.8 0 .3.5.3.5 0 0-.8-.6-1.3-1.3-1.3z"/></svg></span>'+
'<span class="tsvb-tx"><b>Το Trifillakia.gr και στο Viber!</b>Κάντε εγγραφή στο κανάλι μας για να μαθαίνετε πρώτοι όλα τα νέα του Παναθηναϊκού.</span>'+
'<span class="tsvb-bt">ΕΓΓΡΑΦΗ</span>';
body.parentNode.insertBefore(a,body.nextSibling);
}
if(document.readyState!=='loading')run();else document.addEventListener('DOMContentLoaded',run);
})();
