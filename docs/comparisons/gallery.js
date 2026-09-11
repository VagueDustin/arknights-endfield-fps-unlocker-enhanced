'use strict';
const $ = id => document.getElementById(id);
const scenes = {cover:['cover-off','cover-on'],interior:['off','default'],t1:['t1-off','t1-on'],t2:['t2-off','t2-on'],t3:['t3-off','t3-on']};
function position(value) {
  $('slider').value=value;
  $('viewer').style.setProperty('--split', `${value}%`);
  $('status').textContent=`${$('scene').selectedOptions[0].textContent} - ${value}% NR on`;
  document.querySelectorAll('[data-position]').forEach(b=>{const active=b.dataset.position===String(value);b.classList.toggle('active',active);b.setAttribute('aria-pressed',active);});
  document.querySelector('.left').hidden=Number(value)===0;
  document.querySelector('.right').hidden=Number(value)===100;
}
function scene() {
  const interior=$('scene').value==='interior';
  $('variant-label').hidden=!interior;
  const [off,defaultOn]=scenes[$('scene').value];
  const on=interior?$('variant').value:defaultOn;
  $('before').src=`${off}.webp`;$('after').src=`${on}.webp`;
  $('before').alt=`${$('scene').selectedOptions[0].textContent}, neural rendering off`;
  $('after').alt=`${$('scene').selectedOptions[0].textContent}, neural rendering on${interior?', '+$('variant').selectedOptions[0].textContent:''}`;
  $('off-link').href=$('before').src;$('on-link').href=$('after').src;
  position($('slider').value);
}
$('scene').addEventListener('change',scene);$('variant').addEventListener('change',scene);
$('slider').addEventListener('input',e=>position(e.target.value));
document.querySelectorAll('[data-position]').forEach(b=>b.addEventListener('click',()=>position(b.dataset.position)));
scene();
