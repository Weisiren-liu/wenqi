"use strict";

const $ = selector => document.querySelector(selector);
const $$ = selector => Array.from(document.querySelectorAll(selector));
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icon = name => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const state = {data:null,view:"documents",category:"paragraph",mode:"smart",poll:null,filesKey:null,presetsKey:null,previewKey:null,resultsKey:null,formatId:null};
let modalReturnFocus = null;
let toastTimer;
let writing = Promise.resolve();
let nativeWindowDrag = false;
let captionDoubleClickTime = 500;
let lastCaptionPress = null;
const fontPicker = {input:null,choices:[],index:0};
const selectPicker = {select:null,index:0};

function toast(message) {
  const box = $("#toast");
  box.querySelector("span").textContent = String(message || "操作没有完成，请重试。");
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 5000);
}

async function api(method, ...args) {
  if (!window.pywebview?.api) throw new Error("无法连接本地程序，请重新启动文齐。");
  return window.pywebview.api[method](...args);
}

async function action(method, ...args) {
  try {
    const response = await api(method, ...args);
    if (response?.presets) receiveState(response);
    return response;
  } catch (error) {
    toast(error.message || String(error));
    return null;
  }
}

function receiveState(data) {
  state.data = data;
  $(".app").classList.toggle("busy", data.job.running);
  renderFiles();
  renderPresets();
  renderFormat();
  renderPreview();
  renderJob();
  renderResults();
  renderMode();
  const out = data.output;
  $("#output-location span").textContent = out.kind === "beside" ? "原文件旁" : out.path.split(/[\\/]/).filter(Boolean).pop();
  $("#output-location").title = out.kind === "beside" ? "在原文件旁保存新文档" : out.path;
  if (data.job.running && !state.poll) state.poll = setInterval(() => action("get_state"), 350);
  if (!data.job.running && state.poll) { clearInterval(state.poll); state.poll = null; }
  updateDock();
}

function renderFiles() {
  const data = state.data;
  const key = JSON.stringify(data.files);
  const empty = !data.files.length;
  $("#empty-state").hidden = !empty;
  $("#file-state").hidden = empty;
  $("#clear-files").hidden = empty;
  $("#file-count").textContent = `${data.files.length} 个文档`;
  if (key !== state.filesKey) {
    state.filesKey = key;
    $("#file-list").innerHTML = data.files.map(file => `<div class="file-row"><div class="file-thumbnail">${icon("file")}</div><div class="file-details"><div class="file-name" title="${escapeHTML(file.path)}">${escapeHTML(file.name)}</div><div class="file-size">${formatSize(file.size)}</div></div><button class="icon-button remove-file" data-path="${escapeHTML(file.path)}" aria-label="移除 ${escapeHTML(file.name)}">${icon("close")}</button></div>`).join("");
  }
  ["#choose-files","#add-more","#choose-folder","#paste-text","#clear-files","#output-location"].forEach(selector => { $(selector).disabled = data.job.running; });
  $$(".remove-file").forEach(button => { button.disabled = data.job.running; });
}

function formatSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1048576) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1048576).toFixed(1)} MB`;
}

function presetIcon(id) {
  return ({custom:"sliders",official:"file",academic:"book",legal:"scale"})[id] || "file";
}

function renderPresets() {
  const data = state.data;
  const key = JSON.stringify(data.presets);
  if (key !== state.presetsKey) {
    state.presetsKey = key;
    $("#preset-select").innerHTML = data.presets.map(p => `<option value="${escapeHTML(p.id)}">${escapeHTML(p.name)}</option>`).join("");
    const item = p => `<button class="preset-item" data-preset="${escapeHTML(p.id)}" title="${escapeHTML(p.name)}">${icon(presetIcon(p.id))}<span>${escapeHTML(p.name)}</span></button>`;
    const order = {custom:0,official:1,academic:2,legal:3};
    $("#builtin-presets").innerHTML = data.presets.filter(p => p.builtin).sort((a,b) => order[a.id]-order[b.id]).map(item).join("");
    const custom = data.presets.filter(p => !p.builtin);
    $("#custom-presets").innerHTML = custom.map(item).join("");
    $("#no-custom-formats").hidden = custom.length > 0;
  }
  $("#preset-select").value = data.active;
  updateSelectControl($("#preset-select"));
  $$(".preset-item").forEach(button => {
    const selected = button.dataset.preset === data.active;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", selected);
    button.disabled = data.job.running;
  });
}

const alignNames = {left:"左对齐",center:"居中",right:"右对齐",justify:"两端对齐"};
function selectControl(attributes,value,choices,label) {
  return `<div class="select-control"><select ${attributes} hidden>${Object.entries(choices).map(([id,name])=>`<option value="${escapeHTML(id)}" ${String(value)===id?"selected":""}>${escapeHTML(name)}</option>`).join("")}</select><button type="button" class="select-trigger" role="combobox" aria-label="${escapeHTML(label)}" aria-haspopup="listbox" aria-expanded="false" aria-controls="select-picker"><span>${escapeHTML(choices[value]||"")}</span>${icon("down")}</button></div>`;
}

function settingsInput(key,field,value,type="number",label="") {
  const attributes = `data-key="${escapeHTML(key)}" data-field="${field || ""}" aria-label="${escapeHTML(label)}"`;
  if (type === "checkbox") return `<input type="checkbox" ${attributes} ${value?"checked":""}>`;
  if (type === "align") return selectControl(attributes,value,alignNames,label);
  if (type === "spacing") return `<input type="text" ${attributes} title="固定行距输入磅值；多倍行距输入如 1.5倍" value="${escapeHTML(value)}">`;
  if (type === "font") return `<div class="font-control"><input type="text" class="font-input" ${attributes} value="${escapeHTML(value)}" autocomplete="off" maxlength="100" aria-haspopup="dialog" aria-expanded="false" aria-controls="font-picker"><button type="button" class="font-toggle" tabindex="-1" aria-label="选择${escapeHTML(label)}" aria-haspopup="dialog" aria-expanded="false" aria-controls="font-picker">${icon("down")}</button></div>`;
  return `<input type="${type}" ${attributes} min="0" max="576" step="0.5" value="${escapeHTML(value)}">`;
}

function closeFontPicker(returnFocus=false) {
  const input=fontPicker.input;
  if(!input)return;
  input.setAttribute("aria-expanded","false");
  input.nextElementSibling.setAttribute("aria-expanded","false");
  fontPicker.input=null;
  $("#font-picker").hidden=true;
  $("#font-search").removeAttribute("aria-activedescendant");
  if(returnFocus&&input.isConnected&&!input.disabled)input.focus();
}

function positionPicker(picker,anchor,minWidth,maxHeight,preferredBelow=maxHeight) {
  const bounds=anchor.getBoundingClientRect();
  const width=Math.min(Math.max(bounds.width,minWidth),innerWidth-24);
  const below=innerHeight-bounds.bottom-18,above=bounds.top-18;
  const openBelow=below>=preferredBelow||below>=above;
  picker.style.width=`${width}px`;
  picker.style.maxHeight=`${Math.min(maxHeight,openBelow?below:above)}px`;
  picker.style.left=`${Math.max(12,Math.min(bounds.left,innerWidth-width-12))}px`;
  picker.style.top=`${openBelow?bounds.bottom+6:Math.max(12,bounds.top-picker.offsetHeight-6)}px`;
}

function positionFontPicker() {
  if(fontPicker.input)positionPicker($("#font-picker"),fontPicker.input,290,340,280);
}

function updateSelectControl(select) {
  const trigger=select.nextElementSibling;
  trigger.querySelector("span").textContent=select.selectedOptions[0]?.textContent||"";
  trigger.disabled=select.disabled;
  trigger.classList.toggle("changed",select.classList.contains("changed"));
}

function closeSelectPicker(returnFocus=false) {
  const select=selectPicker.select;
  if(!select)return;
  const trigger=select.nextElementSibling;
  trigger.setAttribute("aria-expanded","false");
  trigger.removeAttribute("aria-activedescendant");
  selectPicker.select=null;
  $("#select-picker").hidden=true;
  if(returnFocus&&trigger.isConnected&&!trigger.disabled)trigger.focus();
}

function highlightSelect(index) {
  const options=$$("#select-picker [role=option]");
  selectPicker.index=Math.max(0,Math.min(index,options.length-1));
  options.forEach((option,i)=>option.classList.toggle("active",i===selectPicker.index));
  selectPicker.select.nextElementSibling.setAttribute("aria-activedescendant",options[selectPicker.index].id);
  options[selectPicker.index].scrollIntoView({block:"nearest"});
}

function openSelectPicker(select) {
  if(select.disabled||!select.options.length)return;
  closeSelectPicker();
  closeFontPicker();
  closeMenus();
  selectPicker.select=select;
  const trigger=select.nextElementSibling;
  $("#select-picker").setAttribute("aria-label",trigger.getAttribute("aria-label"));
  trigger.setAttribute("aria-expanded","true");
  $("#select-picker").innerHTML=Array.from(select.options).map((option,index)=>`<button type="button" class="picker-choice" role="option" tabindex="-1" id="select-choice-${index}" data-select-index="${index}" aria-selected="${option.selected}"><span>${escapeHTML(option.textContent)}</span>${option.selected?icon("check"):""}</button>`).join("");
  $("#select-picker").hidden=false;
  positionPicker($("#select-picker"),trigger,160,Math.min(280,select.options.length*33+18));
  highlightSelect(select.selectedIndex);
  trigger.focus();
}

function chooseSelect(index) {
  const select=selectPicker.select;
  if(!select?.options[index])return;
  select.selectedIndex=index;
  updateSelectControl(select);
  closeSelectPicker(true);
  select.dispatchEvent(new Event("change",{bubbles:true}));
}

function highlightFont(index,scroll=true) {
  fontPicker.index=Math.max(0,Math.min(index,fontPicker.choices.length-1));
  $$("#font-choices [role=option]").forEach((option,i)=>option.classList.toggle("active",i===fontPicker.index));
  const option=$("#font-choices .active");
  if(option){
    $("#font-search").setAttribute("aria-activedescendant",option.id);
    if(scroll)option.scrollIntoView({block:"nearest"});
  }else $("#font-search").removeAttribute("aria-activedescendant");
}

function renderFontChoices() {
  const current=fontPicker.input.value.trim(),query=$("#font-search").value.trim();
  // Search independently of the existing value: opening always shows every font.
  const names=[...new Set([current,...(state.data?.fonts||[])].filter(Boolean))];
  const folded=query.toLocaleLowerCase();
  const matches=names.filter(name=>name.toLocaleLowerCase().includes(folded));
  const custom=query&&!names.some(name=>name.toLocaleLowerCase()===folded);
  fontPicker.choices=custom?[...matches,query]:matches;
  $("#font-choices").innerHTML=fontPicker.choices.map((name,index)=>`<button type="button" role="option" tabindex="-1" id="font-choice-${index}" data-font-index="${index}" aria-selected="${name===current}" class="picker-choice ${custom&&index===matches.length?"custom-font":""}"><span>${escapeHTML(custom&&index===matches.length?`使用「${name}」`:name)}</span>${name===current?icon("check"):""}</button>`).join("");
  $("#font-hint").textContent=custom?"可使用输入的字体名称；请确认电脑已安装该字体。":query?`${matches.length} 个匹配字体`:`${names.length} 个字体 · 支持中英文搜索`;
  $("#font-choices").scrollTop=0;
  highlightFont(0,false);
  positionFontPicker();
}

function openFontPicker(input) {
  if(input.disabled)return;
  closeFontPicker();
  closeSelectPicker();
  closeMenus();
  fontPicker.input=input;
  input.setAttribute("aria-expanded","true");
  input.nextElementSibling.setAttribute("aria-expanded","true");
  $("#font-search").value="";
  $("#font-picker").hidden=false;
  renderFontChoices();
  $("#font-search").focus();
}

function chooseFont(index) {
  const input=fontPicker.input,name=fontPicker.choices[index];
  if(!input||name===undefined)return;
  closeFontPicker(true);
  input.value=name;
  input.dispatchEvent(new Event("change",{bubbles:true}));
}

document.addEventListener("click",event=>{
  const trigger=event.target.closest(".select-trigger");
  if(trigger&&!trigger.disabled){
    event.preventDefault();
    const select=trigger.previousElementSibling;
    if(selectPicker.select===select)closeSelectPicker(true);
    else openSelectPicker(select);
  }
  const selectOption=event.target.closest("#select-picker [data-select-index]");
  if(selectOption)chooseSelect(Number(selectOption.dataset.selectIndex));
  const control=event.target.closest(".font-control");
  if(control){
    event.preventDefault();
    const input=control.querySelector(".font-input");
    if(fontPicker.input===input)closeFontPicker(true);
    else openFontPicker(input);
  }
  const option=event.target.closest("#font-choices [data-font-index]");
  if(option)chooseFont(Number(option.dataset.fontIndex));
});
document.addEventListener("pointerdown",event=>{
  if(selectPicker.select&&!event.target.closest(".select-control,#select-picker"))closeSelectPicker();
  if(fontPicker.input&&!event.target.closest(".font-control,#font-picker"))closeFontPicker();
});
document.addEventListener("focusin",event=>{
  if(selectPicker.select&&!event.target.closest(".select-control,#select-picker"))closeSelectPicker();
  if(fontPicker.input&&!event.target.closest(".font-control,#font-picker"))closeFontPicker();
});
document.addEventListener("scroll",event=>{
  if(selectPicker.select&&!$("#select-picker").contains(event.target))closeSelectPicker();
  if(fontPicker.input&&!$("#font-picker").contains(event.target))closeFontPicker();
},true);
$("#font-search").addEventListener("input",renderFontChoices);
document.addEventListener("keydown",event=>{
  if(event.target.matches(".select-trigger")){
    const open=selectPicker.select===event.target.previousElementSibling;
    if(event.key==="ArrowDown"||event.key==="ArrowUp"){
      event.preventDefault();
      if(open)highlightSelect(selectPicker.index+(event.key==="ArrowDown"?1:-1));
      else openSelectPicker(event.target.previousElementSibling);
    }else if(open&&(event.key==="Enter"||event.key===" ")){
      event.preventDefault();chooseSelect(selectPicker.index);
    }else if(open&&(event.key==="Home"||event.key==="End")){
      event.preventDefault();highlightSelect(event.key==="Home"?0:selectPicker.select.options.length-1);
    }else if(open&&event.key==="Escape"){
      event.preventDefault();closeSelectPicker(true);
    }else if(open&&event.key==="Tab")closeSelectPicker();
  }else if(event.target.matches(".font-input")&&event.key==="ArrowDown"){
    event.preventDefault();openFontPicker(event.target);
  }else if(event.target.id==="font-search"){
    if(event.isComposing||event.keyCode===229)return;
    if(event.key==="ArrowDown"||event.key==="ArrowUp"){
      event.preventDefault();event.stopPropagation();highlightFont(fontPicker.index+(event.key==="ArrowDown"?1:-1));
    }else if(event.key==="Enter"){
      event.preventDefault();event.stopPropagation();chooseFont(fontPicker.index);
    }else if(event.key==="Escape"){
      event.preventDefault();event.stopPropagation();closeFontPicker(true);
    }else if(event.key==="Tab")closeFontPicker(true);
  }
});

function renderFormat() {
  const data = state.data, effective = data.effective;
  if(data.job.running||state.formatId!==data.active){closeFontPicker();closeSelectPicker();}
  $("#editor-title").textContent = effective.name;
  const changed = Object.values(data.overrides).reduce((sum,value) => sum + (value && typeof value === "object" ? Object.keys(value).length : 1), 0);
  $("#modified-summary").textContent = changed ? `${changed} 项参数已调整 · 自动保存` : "调整参数后自动保存";
  $("#modified-summary").classList.toggle("modified", changed > 0);
  $("#restore-all").disabled = !changed || data.job.running;
  if (state.formatId !== data.active) {
    state.formatId = data.active;
    const fields = [["font_cn","font"],["font_en","font"],["size","number"],["bold","checkbox"],["align","align"],["indent","number"],["line_spacing","spacing"],["space_before","number"],["space_after","number"]];
    $("#element-table tbody").innerHTML = data.elements.map(([key,label]) => `<tr data-element="${key}"><td>${label}</td>${fields.map(([field,type]) => `<td>${settingsInput(key,field,effective[key]?.[field]??"",type,`${label} ${fieldNames[field]}`)}</td>`).join("")}<td><button class="icon-button restore-row" data-element="${key}" aria-label="恢复${label}默认参数" title="恢复这一行">${icon("reset")}</button></td></tr>`).join("");
    buildSettingsForms();
  }
  $$("#format-view [data-key]").forEach(input => {
    const key = input.dataset.key, field = input.dataset.field || null;
    const value = field ? effective[key]?.[field] : effective[key];
    if (document.activeElement !== input) {
      if (input.type === "checkbox") input.checked = Boolean(value);
      else input.value = value ?? "";
    }
    const altered = field ? Object.hasOwn(data.overrides[key] || {},field) : Object.hasOwn(data.overrides,key);
    input.classList.toggle("changed",altered);
    input.disabled = data.job.running;
  });
  $$(".font-toggle").forEach(button=>{button.disabled=data.job.running;});
  $$(".select-control select").forEach(updateSelectControl);
  $$("#element-table tr[data-element]").forEach(row => { row.classList.toggle("modified", Boolean(data.overrides[row.dataset.element])); });
  const builtin = data.presets.find(p => p.id === data.active)?.builtin;
  $$("[data-action=rename-format],[data-action=delete-format]").forEach(button => { button.disabled = builtin || data.job.running; });
}

const fieldNames = {font_cn:"中文字体",font_en:"英数字体",size:"字号",bold:"加粗",align:"对齐",indent:"首行缩进",line_spacing:"行距",space_before:"段前间距",space_after:"段后间距"};
function formField(label,key,field=null,{type="number",unit="",choices=null}={}) {
  const value = field ? state.data.effective[key]?.[field] : state.data.effective[key];
  let control;
  if (choices) control = selectControl(`data-key="${escapeHTML(key)}" data-field="${field||""}" aria-label="${escapeHTML(label)}"`,value,choices,label);
  else control = settingsInput(key,field,value,type,label);
  return `<label class="form-field"><span>${label}</span>${unit?`<div class="field-unit">${control}<span>${unit}</span></div>`:control}</label>`;
}
function toggleField(label,key,field=null) {
  const value = field ? state.data.effective[key]?.[field] : state.data.effective[key];
  return `<label class="toggle-row"><span>${label}</span>${settingsInput(key,field,value,"checkbox",label)}<span class="toggle"></span></label>`;
}
function buildSettingsForms() {
  $("#page-settings").innerHTML = `<section class="settings-group"><h3>页边距</h3><div class="form-grid">${[["top","上"],["bottom","下"],["left","左"],["right","右"]].map(([key,label]) => formField(label,"page",key,{unit:"cm"})).join("")}</div></section><section class="settings-group"><h3>页码</h3>${toggleField("显示页码","page_number")}<div class="form-grid" style="margin-top:14px">${formField("样式","page_number_style",null,{choices:{dash:"— 1 —",plain:"1",page_text:"第 1 页",page_total:"1 / 总页数"}})}${formField("位置","page_number_position",null,{choices:{outside:"外侧",center:"居中",left:"左侧",right:"右侧"}})}${formField("字体","page_number_font",null,{type:"font"})}${formField("字号","page_number_size",null,{unit:"pt"})}${formField("距页脚边缘","page_number_offset_mm",null,{unit:"mm"})}</div>${toggleField("替换已有页码","replace_existing_page_number")}</section>`;
  $("#table-settings").innerHTML = `<section class="settings-group"><h3>表格文字</h3><div class="form-grid">${formField("中文字体","table","font_cn",{type:"font"})}${formField("英数字体","table","font_en",{type:"font"})}${formField("字号","table","size",{unit:"pt"})}${formField("行距","table","line_spacing",{type:"spacing",unit:"pt"})}${formField("首行缩进","table","first_line_indent",{unit:"pt"})}</div></section><section class="settings-group"><h3>表格布局</h3>${toggleField("表格文字加粗","table","bold")}${toggleField("表头加粗","table","header_bold")}${toggleField("根据内容自动对齐","table","smart_align")}</section>`;
  $("#behavior-settings").innerHTML = `<section class="settings-group"><h3>文字处理</h3><div class="form-grid">${formField("空格处理","space_handling",null,{choices:{remove_all:"移除中文之间的空格",keep_all:"保留空格",keep_en_boundary:"保留中英文之间的空格"}})}</div>${toggleField("主标题加粗","first_line_bold")}${toggleField("标题序号加粗","bold_serial")}${toggleField("在标点处拆分标题","split_heading_at_punct")}</section><section class="settings-group"><h3>样式清理</h3>${toggleField("清理已有文档样式","deep_clean")}<p class="form-help">清理已有字体、颜色和段落样式后，应用当前格式。</p></section>`;
}

function renderPreview() {
  const data=state.data;
  const key=JSON.stringify([data.preview,data.effective,state.mode]);
  if(key===state.previewKey)return;
  state.previewKey=key;
  const preset=data.effective;
  $("#preview-format-name").textContent = state.mode === "smart" ? preset.name : state.mode === "analyze" ? "检查原文档，不修改文件" : "保留原有排版";
  $("#preview-source").textContent=data.previewIsSample?"示例文档":data.files[0]?.name||"";
  $(".preview-heading>span").textContent=state.mode==="smart"?"格式预览":"原文预览";
  const paper=$("#preview-paper");
  const ratio=paper.getBoundingClientRect().width/595.28;
  const page=preset.page||{top:3.7,bottom:3.5,left:2.8,right:2.6};
  paper.style.padding=`${page.top/21*100}% ${page.right/21*100}% ${page.bottom/21*100}% ${page.left/21*100}%`;
  // Percent padding resolves against the parent's width; use paper pixels instead.
  paper.style.padding=`${page.top/21*paper.clientWidth}px ${page.right/21*paper.clientWidth}px ${page.bottom/21*paper.clientWidth}px ${page.left/21*paper.clientWidth}px`;
  $("#paper-content").innerHTML=data.preview.map(paragraph=>{
    const settings=state.mode==="smart"?(preset[paragraph.element]||preset.body):{font_cn:"仿宋",font_en:"Times New Roman",size:16,align:paragraph.element==="title"?"center":"justify",line_spacing:28,indent:paragraph.element==="body"?32:0};
    const text=document.createElement("p");
    text.dataset.element=paragraph.element;
    text.textContent=paragraph.text;
    text.style.fontFamily=`"${String(settings.font_en||"Times New Roman").replace(/["\\]/g,"")}", "${String(settings.font_cn||"仿宋").replace(/["\\]/g,"")}", serif`;
    text.style.fontSize=`${Math.max(7,(settings.size||16)*ratio)}px`;
    text.style.fontWeight=settings.bold?"700":"400";
    text.style.textAlign=settings.align||"left";
    const line=settings.line_spacing;
    text.style.lineHeight=typeof line==="number"?`${Math.max(10,line*ratio)}px`:String(line||"1.8").replace("倍","");
    text.style.textIndent=`${(settings.indent||0)*ratio}px`;
    text.style.marginTop=`${(settings.space_before||0)*ratio}px`;
    text.style.marginBottom=`${(settings.space_after||0)*ratio}px`;
    if(paragraph.element==="title")text.style.marginBottom=`${Math.max(8,(settings.space_after||0)*ratio)}px`;
    return text.outerHTML;
  }).join("");
  $("#paper-page-number").hidden=!preset.page_number||state.mode!=="smart";
  $("#paper-page-number").textContent=preset.page_number_style==="dash"?"— 1 —":preset.page_number_style==="page_text"?"第 1 页":preset.page_number_style==="page_total"?"1 / N":"1";
  $("#paper-page-number").style.textAlign=preset.page_number_position==="outside"?"right":preset.page_number_position||"center";
  $("#paper-page-number").style.paddingLeft=`${page.left/21*paper.clientWidth}px`;
  $("#paper-page-number").style.paddingRight=`${page.right/21*paper.clientWidth}px`;
  $("#paper-page-number").style.bottom=`${Math.max(.4,page.bottom-(preset.page_number_offset_mm||0)/10)/21*paper.clientWidth}px`;
  $("#paper-page-number").style.fontSize=`${(preset.page_number_size||14)*ratio}px`;
}

function renderJob(){
  const job=state.data.job;
  $("#job-panel").hidden=!job.running;
  $("#job-title").textContent=state.mode==="analyze"?"正在诊断":"正在处理";
  $("#job-percent").textContent=`${job.percent}%`;
  $("#job-progress").style.width=`${job.percent}%`;
  $("#job-stage").textContent=job.stage;
}

function renderResults(){
  const {results,job}=state.data;
  $("#result-panel").hidden=!results.length||job.running;
  const key=JSON.stringify([results,job.running,job.cancelled]);
  if(key===state.resultsKey)return;
  state.resultsKey=key;
  if(!results.length)return;
  const errors=results.filter(r=>r.status==="error").length;
  const diagnosis=results.some(r=>r.diagnosis);
  let title=job.cancelled?"处理已停止":errors===results.length?"处理未完成":errors?`已完成 ${results.length-errors} 个，${errors} 个未完成`:diagnosis?"诊断完成":"处理完成";
  $("#result-panel").innerHTML=`<div class="result-title ${errors?"error":""}">${icon(errors?"alert":"check")}<span>${title}</span></div>`+results.map(result=>{
    if(result.status==="error")return `<div class="result-file"><span>${escapeHTML(result.name)}</span></div><p class="error-description">${escapeHTML(result.error)}</p>`;
    if(result.diagnosis){
      const labels={punctuation:"标点",numbering:"编号",paragraph:"段落",font:"字体"};
      return (results.length>1?`<div class="file-name">${escapeHTML(result.name)}</div>`:"")+Object.entries(result.diagnosis).map(([group,issues])=>`<details class="diagnosis-group"><summary>${labels[group]}<span>${issues.length?`${issues.length} 项待检查`:"未发现问题"}</span></summary>${issues.length?`<ul>${issues.slice(0,100).map(issue=>`<li>${escapeHTML(describeIssue(issue))}</li>`).join("")}</ul>`:""}</details>`).join("");
    }
    return `<div class="result-file"><span>${escapeHTML(result.path.split(/[\\/]/).pop())}</span><button class="quiet-button open-result" data-path="${escapeHTML(result.path)}">打开</button><button class="icon-button open-folder" data-path="${escapeHTML(result.path)}" aria-label="打开所在文件夹">${icon("folder")}</button></div>`;
  }).join("");
  if(!job.running&&state.view==="documents")requestAnimationFrame(()=>{
    const workspace=$("#documents-view");
    const excess=$("#result-panel").getBoundingClientRect().bottom-workspace.getBoundingClientRect().bottom;
    if(excess>0)workspace.scrollTop+=excess+12;
  });
}

function describeIssue(issue){
  if(typeof issue==="string")return issue;
  const prefix=issue.para?`第 ${issue.para} 段：`:"";
  const parts=Object.entries(issue).filter(([key])=>key!=="para").map(([key,value])=>{
    if(Array.isArray(value))return value.join("、");
    if(value&&typeof value==="object")return Object.values(value).join("、");
    return String(value);
  });
  return prefix+parts.join(" · ");
}

function updateDock(){
  const data=state.data;
  if(!data)return;
  const {job,files,results}=data;
  $("#dock-status").textContent=job.running?job.stage:job.cancelled?"已停止处理":results.length?`${results.filter(r=>r.status==="success").length} 个文档已完成`:files.length?`${files.length} 个文档已就绪`:"等待添加文档";
  $("#status-dot").className=`status-dot ${job.running?"running":results.length?"complete":files.length?"ready":""}`;
  const button=$("#start-processing");
  button.disabled=!files.length;
  button.classList.toggle("cancel",job.running);
  button.querySelector("span").textContent=job.running?"停止处理":state.mode==="analyze"?"开始诊断":"开始处理";
  button.querySelector("use").setAttribute("href",job.running?"#i-close":"#i-arrow");
}

function renderMode(){
  $$("[data-mode]").forEach((button,index)=>{
    const active=button.dataset.mode===state.mode;
    button.classList.toggle("active",active);button.setAttribute("aria-pressed",active);
    button.disabled=state.data?.job.running||false;
    if(active)$(".segment-lens").style.transform=`translateX(${index*100}%)`;
  });
  $("#preset-option").hidden=state.mode!=="smart";
  $("#output-option").hidden=state.mode==="analyze";
  $("#more-options-toggle").hidden=state.mode!=="smart";
  $("#more-options").hidden=state.mode!=="smart"||$("#more-options-toggle").getAttribute("aria-expanded")!=="true";
  if(state.data){$("#preset-select").disabled=state.data.job.running;updateSelectControl($("#preset-select"));}
}

function setView(view){
  closeFontPicker();
  closeSelectPicker();
  state.view=view;
  $("#documents-view").hidden=view!=="documents";
  $("#format-view").hidden=view!=="format";
  $(".view-switch").dataset.current=view;
  $$("[data-view]").forEach(button=>{const active=button.dataset.view===view;button.classList.toggle("active",active);button.setAttribute("aria-selected",active);});
  if(view==="documents"){state.previewKey=null;if(state.data)renderPreview();}
}

function setCategory(category){
  closeFontPicker();
  closeSelectPicker();
  state.category=category;
  $$("[data-category]").forEach(button=>button.classList.toggle("active",button.dataset.category===category));
  ["paragraph","page","table","behavior"].forEach(id=>{$(`#${id}-settings`).hidden=id!==category;});
}

function openModal(title,content,buttons=[],className=""){
  closeFontPicker();
  closeSelectPicker();
  closeMenus();
  modalReturnFocus=document.activeElement;
  $("#modal-title").textContent=title;
  $("#modal-content").innerHTML=content;
  $("#modal").className=`modal glass ${className}`;
  $("#modal-actions").innerHTML="";
  buttons.forEach(({label,primary=false,run})=>{
    const button=document.createElement("button");button.className=`button ${primary?"primary-button":"secondary-button"}`;button.textContent=label;
    button.onclick=async()=>{
      button.disabled=true;
      try{await run();}catch(error){
        $(".modal-error")?.remove();const paragraph=document.createElement("p");paragraph.className="modal-error";paragraph.textContent=error.message||String(error);$("#modal-content").append(paragraph);
      }finally{button.disabled=false;}
    };
    $("#modal-actions").append(button);
  });
  $("#modal-backdrop").hidden=false;
  $("#app").inert=true;
  requestAnimationFrame(()=>($("#modal-content input")||$("#modal-close")).focus());
}

function closeModal(){
  $("#modal-backdrop").hidden=true;$("#app").inert=false;
  if(modalReturnFocus?.isConnected)modalReturnFocus.focus();
}

function nameModal(actionName="save"){
  const rename=actionName==="rename";
  openModal(rename?"重命名格式":"存为新格式",`<p class="modal-description">${rename?"为这个格式选择一个名称。":"保存当前全部参数，下次可以直接使用。"}</p><input id="format-name" type="text" maxlength="60" aria-label="格式名称" value="${rename?escapeHTML(state.data.effective.name):""}" placeholder="格式名称">`,[
    {label:"取消",run:closeModal},
    {label:"保存",primary:true,run:async()=>{
      const name=$("#format-name").value;
      const response=rename?await api("manage_preset","rename",name):await api("save_preset",name);
      receiveState(response);closeModal();toast("格式已保存");
    }}
  ]);
}

function pasteModal(){
  openModal("粘贴文本",`<input id="paste-title" type="text" aria-label="文档标题" placeholder="标题（可选）"><textarea id="paste-body" aria-label="正文" placeholder="在这里粘贴正文…"></textarea><label class="toggle-row"><span>按 Markdown 解析</span><input id="paste-markdown" type="checkbox" role="switch"><span class="toggle"></span></label>`,[
    {label:"取消",run:closeModal},{label:"添加文档",primary:true,run:async()=>{
      const response=await api("create_from_text",$("#paste-title").value,$("#paste-body").value,$("#paste-markdown").checked);
      receiveState(response);closeModal();setView("documents");
    }}
  ],"paste-modal");
}

function outputModal(){
  openModal("保存位置",`<button class="output-choice" data-output="beside">${icon("file")}<span>原文件旁</span>${icon("chevron")}</button><button class="output-choice" data-output="folder">${icon("folder")}<span>选择文件夹</span>${icon("chevron")}</button>${state.data.files.length===1?`<button class="output-choice" data-output="file">${icon("edit")}<span>指定文件名称与格式</span>${icon("chevron")}</button>`:""}`);
}

function logsModal(){
  const logs=state.data.logs;
  openModal("运行日志",logs.length?`<div class="logs">${logs.map(item=>`<div class="log-entry ${escapeHTML(item.level)}"><time>${escapeHTML(item.time)}</time><span>${escapeHTML(item.message)}</span></div>`).join("")}</div>`:`<p class="modal-description">处理文档后，详细记录会显示在这里。</p>`);
}

function aboutModal(){
  openModal("关于文齐",`<div class="about-brand"><span class="about-symbol">${icon("file")}</span><div><h3>文齐</h3><p>版本 ${escapeHTML(state.data.version)}</p></div></div><div class="about-copy"><p>文档排版与标点修复，在本地完成。</p><p>基于 docformat-gui MIT 版二次开发。</p><p>原作者：KaguraNanaga · 维护：Weisiren-liu</p><p>Copyright © 2025 KaguraNanaga</p><p>许可证：MIT License</p></div>`);
}

function closeMenus(){
  $("#app-menu").hidden=true;$("#preset-menu").hidden=true;
  $("#app-menu-toggle").setAttribute("aria-expanded","false");
}

async function start(){
  if(!state.data)return;
  if(state.data.job.running){await action("cancel_processing");return;}
  if(!state.data.files.length){await action("choose_files");return;}
  setView("documents");
  await action("start_processing",{mode:state.mode,revision:$("#revision").checked,autoOpen:$("#auto-open").checked});
}

document.addEventListener("click",async event=>{
  const button=event.target.closest("button");
  if(!button||button.disabled)return;
  if(button.dataset.view)setView(button.dataset.view);
  if(button.dataset.mode){state.mode=button.dataset.mode;renderMode();if(state.data){renderPreview();updateDock();}}
  if(button.dataset.category)setCategory(button.dataset.category);
  if(button.dataset.window){const result=await action("window_action",button.dataset.window);if(result)receiveWindowState(result);}
  if(button.dataset.preset)await action("select_preset",button.dataset.preset);
  if(button.classList.contains("remove-file"))await action("remove_file",button.dataset.path);
  if(button.classList.contains("restore-row"))await action("restore_settings",button.dataset.element);
  if(button.classList.contains("open-result"))await action("open_result",button.dataset.path,false);
  if(button.classList.contains("open-folder"))await action("open_result",button.dataset.path,true);
  if(button.dataset.output){const kind=button.dataset.output;closeModal();await action("choose_output",kind);}
  const operations={"choose-files":()=>action("choose_files"),"add-more":()=>action("choose_files"),"choose-folder":()=>action("choose_folder"),"clear-files":()=>action("clear_files"),"paste-text":pasteModal,"edit-format":()=>setView("format"),"preview-edit":()=>setView("format"),"output-location":outputModal,"start-processing":start,"modal-close":closeModal,"save-format-rail":()=>nameModal(),"import-format":()=>action("manage_preset","import")};
  if(operations[button.id])await operations[button.id]();
  if(button.id==="more-options-toggle"){
    const expanded=button.getAttribute("aria-expanded")==="true";
    button.setAttribute("aria-expanded",!expanded);$("#more-options").hidden=expanded;
  }
  if(button.id==="app-menu-toggle"){
    const hidden=$("#app-menu").hidden;closeMenus();$("#app-menu").hidden=!hidden;button.setAttribute("aria-expanded",hidden);
  }else if(button.id==="preset-menu-toggle"){
    const hidden=$("#preset-menu").hidden;closeMenus();$("#preset-menu").hidden=!hidden;
  }else if(!button.closest(".popover"))closeMenus();
  if(button.id==="restore-all")openModal("恢复默认参数",`<p class="modal-description">恢复「${escapeHTML(state.data.effective.name)}」的全部参数。已保存的其他格式不受影响。</p>`,[{label:"取消",run:closeModal},{label:"恢复",primary:true,run:async()=>{receiveState(await api("restore_settings"));closeModal();}}]);
  const actionName=button.dataset.action;
  if(actionName){
    closeMenus();
    if(actionName==="logs")logsModal();
    if(actionName==="about")aboutModal();
    if(actionName==="save-format")nameModal();
    if(actionName==="rename-format")nameModal("rename");
    if(actionName==="import-preset")await action("manage_preset","import");
    if(actionName==="export-preset")await action("manage_preset","export");
    if(actionName==="delete-format")openModal("删除格式",`<p class="modal-description">删除「${escapeHTML(state.data.effective.name)}」？</p>`,[{label:"取消",run:closeModal},{label:"删除",primary:true,run:async()=>{receiveState(await api("manage_preset","delete"));closeModal();}}]);
  }
});

document.addEventListener("change",event=>{
  const input=event.target;
  if(input.id==="preset-select"){action("select_preset",input.value);return;}
  if(input.dataset.key){
    const key=input.dataset.key,field=input.dataset.field||null;
    let value=input.type==="checkbox"?input.checked:input.value;
    if(input.type==="number")value=input.value===""?null:Number(input.value);
    writing=writing.then(async()=>{
      const result=await action("update_setting",key,field,value);
      if(!result&&state.data)renderFormat();
    });
  }
});

$("#modal-backdrop").addEventListener("click",event=>{if(event.target.id==="modal-backdrop")closeModal();});
document.addEventListener("keydown",event=>{
  if(event.defaultPrevented)return;
  if(event.key==="Escape"){if(!$("#modal-backdrop").hidden)closeModal();else closeMenus();}
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="o"){event.preventDefault();action("choose_files");}
  if((event.ctrlKey||event.metaKey)&&event.key==="Enter"&&$("#modal-backdrop").hidden){event.preventDefault();start();}
  if(!$("#modal-backdrop").hidden&&event.key==="Tab"){
    const focusable=$$("#modal button,#modal input,#modal textarea,#modal select").filter(el=>!el.disabled&&el.offsetParent);
    const first=focusable[0],last=focusable.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});

let dragDepth=0;
$("#drop-zone").addEventListener("dragenter",event=>{event.preventDefault();dragDepth++;if(!state.data?.job.running)$("#drop-zone").classList.add("drag-over");});
$("#drop-zone").addEventListener("dragleave",()=>{dragDepth--;if(dragDepth<=0){dragDepth=0;$("#drop-zone").classList.remove("drag-over");}});
$("#drop-zone").addEventListener("drop",()=>{dragDepth=0;$("#drop-zone").classList.remove("drag-over");});
document.addEventListener("dragover",event=>event.preventDefault());
document.addEventListener("drop",event=>event.preventDefault());

// A smooth convex edge displacement map bends the real backdrop near the glass rim.
// The center stays optically quiet so labels remain legible.
function installGlass(){
  const ns="http://www.w3.org/2000/svg",defs=$(".svg-definitions defs");
  let count=0;
  const observer=new ResizeObserver(entries=>{
    for(const entry of entries){
      const target=entry.target;
      const bounds=target.getBoundingClientRect();
      const width=Math.round(bounds.width),height=Math.round(bounds.height);
      if(width<10||height<10||target.dataset.glassSize===`${width},${height}`)continue;
      target.dataset.glassSize=`${width},${height}`;
      const radius=Math.min(parseFloat(getComputedStyle(target).borderRadius)||20,width/2,height/2);
      const canvas=document.createElement("canvas");canvas.width=width;canvas.height=height;
      const context=canvas.getContext("2d"),image=context.createImageData(width,height);
      const rim=Math.min(17,radius*.72),cx=width/2,cy=height/2;
      for(let y=0;y<height;y++)for(let x=0;x<width;x++){
        const qx=Math.abs(x-cx)-(cx-radius),qy=Math.abs(y-cy)-(cy-radius);
        const ox=Math.max(qx,0),oy=Math.max(qy,0),length=Math.hypot(ox,oy);
        const distance=length+Math.min(Math.max(qx,qy),0)-radius;
        const edge=distance<=0?Math.max(0,1+distance/rim):0;
        let nx=0,ny=0;
        if(length>0){nx=ox/length*Math.sign(x-cx);ny=oy/length*Math.sign(y-cy);}
        else if(qx>qy)nx=Math.sign(x-cx);else ny=Math.sign(y-cy);
        const offset=(y*width+x)*4;
        image.data[offset]=128+nx*edge*edge*82;
        image.data[offset+1]=128+ny*edge*edge*82;
        image.data[offset+2]=128;image.data[offset+3]=255;
      }
      context.putImageData(image,0,0);
      let filter=target._glassFilter;
      if(!filter){
        filter=document.createElementNS(ns,"filter");filter.id=`glass-lens-${++count}`;
        filter.setAttribute("filterUnits","userSpaceOnUse");filter.setAttribute("x","0");filter.setAttribute("y","0");
        filter.setAttribute("color-interpolation-filters","sRGB");
        const map=document.createElementNS(ns,"feImage");map.setAttribute("result","map");
        const bend=document.createElementNS(ns,"feDisplacementMap");bend.setAttribute("in","SourceGraphic");bend.setAttribute("in2","map");bend.setAttribute("scale","14");bend.setAttribute("xChannelSelector","R");bend.setAttribute("yChannelSelector","G");
        filter.append(map,bend);defs.append(filter);target._glassFilter=filter;
        target.style.backdropFilter=`url(#${filter.id}) blur(18px) saturate(1.25)`;
      }
      filter.setAttribute("width",width);filter.setAttribute("height",height);
      filter.firstChild.setAttribute("width",width);filter.firstChild.setAttribute("height",height);filter.firstChild.setAttribute("href",canvas.toDataURL());
    }
  });
  $$(".glass").forEach(surface=>observer.observe(surface));
}

function receiveWindowState(value){
  nativeWindowDrag=Boolean(value.nativeDrag);
  captionDoubleClickTime=value.doubleClickTime||500;
  document.body.classList.toggle("native-window-controls",nativeWindowDrag);
  document.body.classList.toggle("window-maximized",Boolean(value.maximized));
  $("#app").classList.toggle("is-maximized",Boolean(value.maximized));
  const button=$("[data-window=maximize]");
  button.setAttribute("aria-label",value.maximized?"还原窗口":"最大化窗口");
  button.title=value.maximized?"还原窗口":"最大化窗口";
  button.querySelector("svg").innerHTML=value.maximized?'<path d="M5.5 3.5h7v7M3.5 5.5h7v7h-7Z"/>':'<rect x="3.5" y="3.5" width="9" height="9" rx="1"/>';
}
$(".titlebar").addEventListener("mousedown",event=>{
  if(event.button!==0||event.target.closest("button,select,input,a"))return;
  const now=performance.now();
  const doublePress=event.detail>=2||(lastCaptionPress&&now-lastCaptionPress.time<captionDoubleClickTime&&Math.abs(event.screenX-lastCaptionPress.x)<4&&Math.abs(event.screenY-lastCaptionPress.y)<4);
  lastCaptionPress=doublePress?null:{time:now,x:event.screenX,y:event.screenY};
  if(doublePress){event.preventDefault();action("window_action","maximize").then(result=>{if(result)receiveWindowState(result);});}
  else if(nativeWindowDrag){event.preventDefault();action("begin_window_drag");}
});
$(".resize-handles").addEventListener("mousedown",event=>{
  if(event.button!==0||!event.target.dataset.resize)return;
  event.preventDefault();event.stopPropagation();action("begin_window_resize",event.target.dataset.resize);
});
window.wenqi={receiveState,toast,setView,setCategory,receiveWindowState};
window.addEventListener("pywebviewready",async()=>{
  try{receiveState(await api("get_state"));receiveWindowState(await api("window_state"));document.body.classList.remove("loading");}
  catch(error){toast(error.message||String(error));}
});
window.addEventListener("resize",()=>{closeFontPicker();closeSelectPicker();state.previewKey=null;if(state.data)renderPreview();});
$("#start-processing").disabled=true;
$(".view-switch").setAttribute("role","tablist");
$$("[data-view]").forEach(button=>button.setAttribute("role","tab"));
document.body.classList.add("loading");
installGlass();
