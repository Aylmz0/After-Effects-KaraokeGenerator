// After Effects için Gelişmiş Karaoke Efekti Scripti
function parseJSON(t){
	try{
		return eval("("+t+")");
	}catch(e){
		try{
			return JSON.parse(t);
		}catch(e2){
			throw new Error("JSON ayrıştırılamadı: "+e2.message);
		}
	}
}

function showSettingsDialog(){
	var d=new Window("dialog","Metin Gösterici Ayarları");
	d.orientation="column";d.alignChildren=["left","top"];d.spacing=10;d.margins=16;
	
	// UI Elemanları
	var a=d.add("panel",undefined,"Animasyon Ayarları");a.orientation="column";a.alignChildren=["left","top"];a.spacing=5;a.margins=10;
	var b=a.add("group");b.add("statictext",undefined,"Animasyon Tipi:");
	var c=b.add("dropdownlist",undefined,["Harf Harf Açılma","Anında Görünme"]);c.selection=0;
	var e=a.add("group");e.add("statictext",undefined,"Animasyon Hızı (%):");var f=e.add("edittext",undefined,"100");f.characters=5;
	
	var g=d.add("panel",undefined,"Font Ayarları");g.orientation="column";g.alignChildren=["left","top"];g.spacing=5;g.margins=10;
	var h=g.add("group");h.add("statictext",undefined,"Font Boyutu:");var i=h.add("edittext",undefined,"30");i.characters=5;
	
	var j=d.add("panel",undefined,"Cümle Ayarları");j.orientation="column";j.alignChildren=["left","top"];j.spacing=5;j.margins=10;
	var k=j.add("group");k.add("statictext",undefined,"Minimum Karakter Sayısı:");var l=k.add("edittext",undefined,"50");l.characters=5;
	var m=j.add("group");m.add("statictext",undefined,"Maksimum Karakter Sayısı:");var n=m.add("edittext",undefined,"55");n.characters=5;
	
	var o=d.add("panel",undefined,"Pozisyon Ayarları");o.orientation="column";o.alignChildren=["left","top"];o.spacing=5;o.margins=10;
	var p=o.add("group");p.add("statictext",undefined,"Hizalama:");var q=p.add("dropdownlist",undefined,["Ortala","Sol","Sağ"]);q.selection=1;
	var r=o.add("group");r.add("statictext",undefined,"X Pozisyonu (%):");var s=o.add("edittext",undefined,"10");s.characters=5;
	var t=o.add("group");t.add("statictext",undefined,"Y Pozisyonu (%):");var u=o.add("edittext",undefined,"10");u.characters=5;
	
	var v=d.add("group");v.alignment="center";
	var w=v.add("button",undefined,"Tamam",{name:"ok"});
	var x=v.add("button",undefined,"İptal",{name:"cancel"});
	
	if(d.show()==1)return{fontSize:parseInt(i.text),minChars:parseInt(l.text),maxChars:parseInt(n.text),alignment:q.selection.index,xPosition:parseInt(s.text),yPosition:parseInt(u.text),animationType:c.selection.index,animationSpeed:parseFloat(f.text)/100};
	return null;
}

function parseColor(c){var p=c.split(",");if(p.length!=3)return[255,255,255];function t(s){while(s.charAt(0)==" ")s=s.substring(1);while(s.charAt(s.length-1)==" ")s=s.substring(0,s.length-1);return s}return[parseInt(t(p[0])),parseInt(t(p[1])),parseInt(t(p[2]))]}

function combineShortSentences(s,min,max){
	function t(s){if(!s||typeof s!="string")return"";while(s.length>0&&(s.charAt(0)==" "||s.charAt(0)=="\n"||s.charAt(0)=="\r"||s.charAt(0)=="\t"))s=s.substring(1);while(s.length>0&&(s.charAt(s.length-1)==" "||s.charAt(s.length-1)=="\n"||s.charAt(s.length-1)=="\r"||s.charAt(s.length-1)=="\t"))s=s.substring(0,s.length-1);return s}
	if(!s||s.length===0)return[];var r=[],c=null;
	for(var i=0;i<s.length;i++){
		var e=s[i];if(!e||typeof e!='object')e={text:"",start:0,end:0};
		if(typeof e.text!='string')e.text="";
		if(typeof e.start!='number')e.start=(c&&typeof c.end==='number')?c.end:0;
		if(typeof e.end!='number')e.end=e.start+1;
		var x=t(e.text);
		if(c===null){c={text:e.text,start:e.start,end:e.end,l:x.length}}else{
			var d=(e.start!==undefined&&c.end!==undefined)?Math.abs(c.end-e.start):1.0;
			var p=c.text+" "+e.text,y=t(p).length;
			if(c.l<min||(y<=max&&d<0.5)){c.text=p;c.end=e.end;c.l=y}else{
				c.text=t(c.text);if(c.text.length>0)r.push(c);
				c={text:e.text,start:e.start,end:e.end,l:x.length};
			}
		}
	}
	if(c!==null){c.text=t(c.text);if(c.text.length>0)r.push(c)}
	return r;
}

function createPageBasedTextDisplay(c,s,o){
	if(!s||s.length===0){alert("İşlenecek cümle bulunamadı!");return[]}
	var p=Math.ceil(s.length/o.maxLines),r=[];
	for(var i=0;i<p;i++){
		var a=i*o.maxLines,e=Math.min((i+1)*o.maxLines,s.length),l=s.slice(a,e);
		if(l.length===0)continue;
		if(!l[0]||l[0].start===undefined){alert("Sayfa "+(i+1)+" için başlangıç zamanı bulunamadı!");continue}
		var m=l[0].start,n=(i<p-1&&s[e]&&s[e].start!==undefined)?s[e].start:(l[l.length-1]&&l[l.length-1].end!==undefined?l[l.length-1].end+2:m+10);
		
		// İnaktif Katman
		var x=c.layers.addText("");x.name="Sayfa "+(i+1)+" - İnaktif";x.startTime=m;x.outPoint=n;
		var y=x.property("ADBE Text Properties").property("ADBE Text Document"),z=y.value;
		z.text=l.map(function(e){return e.text||""}).join("\n").replace(/\n$/,"");
		z.fontSize=o.fontSize;z.leading=o.fontSize*(o.lineSpacing/100);
		z.justification=o.alignment===0?ParagraphJustification.CENTER_JUSTIFY:o.alignment===1?ParagraphJustification.LEFT_JUSTIFY:ParagraphJustification.RIGHT_JUSTIFY;
		y.setValue(z);
		
		// Aktif Katman
		var a=c.layers.addText("");a.name="Sayfa "+(i+1)+" - Aktif";a.startTime=m;a.outPoint=n;
		var b=a.property("ADBE Text Properties").property("ADBE Text Document"),d=b.value;
		d.fontSize=o.fontSize;d.leading=o.fontSize*(o.lineSpacing/100);
		d.justification=o.alignment===0?ParagraphJustification.CENTER_JUSTIFY:o.alignment===1?ParagraphJustification.LEFT_JUSTIFY:ParagraphJustification.RIGHT_JUSTIFY;
		b.setValue(d);
		
		// Expression
		var expression="";
		expression+="var currentTime = time;\n";
		expression+="var result = \"\";\n\n";
		expression+="// Metni harf harf açma fonksiyonu\n";
		expression+="function animateText(text, startTime, endTime, currentTime, speedFactor) {\n";
		expression+="  var textLength = text.length;\n";
		expression+="  var duration = (endTime - startTime) / speedFactor;\n";
		expression+="  if (duration <= 0) return text; // Prevent division by zero and handle zero duration\n";
		expression+="  var charDuration = duration / textLength;\n";
		expression+="  if (charDuration <= 0) return text; // Prevent division by zero for charDuration\n";
		expression+="  var elapsed = currentTime - startTime;\n";
		expression+="  var visibleChars = Math.floor(elapsed / charDuration);\n";
		expression+="  visibleChars = Math.max(0, Math.min(textLength, visibleChars));\n";
		expression+="  return text.substring(0, visibleChars);\n";
		expression+="}\n\n";
		
		for(var j=0;j<l.length;j++){
			if(!l[j]||!l[j].text)continue;
			var safeText="";
			try{
				safeText=String(l[j].text).replace(/"/g,'\\"').replace(/\n/g,'\\n');
			}catch(e){
				safeText="Metin hatası";
			}
			var startTime=l[j].start||0;
			var endTime=l[j].end||(startTime+5);
			var lineBreak=(j<l.length-1)?"\\n":"";
			expression+="if(currentTime>="+startTime+"){\n";
			expression+="  if(currentTime<"+endTime+"){\n";
			if(o.animationType===0){
				expression+="    var displayText=animateText(\""+safeText+"\", "+startTime+", "+endTime+", currentTime, "+o.animationSpeed+");\n";
				expression+="    result+=displayText+\""+lineBreak+"\";\n";
			}else{
				expression+="    result+=\""+safeText+"\"+\""+lineBreak+"\";\n";
			}
			expression+="  }else{\n";
			expression+="    result+=\""+safeText+"\"+\""+lineBreak+"\";\n";
			expression+="  }\n";
			expression+="}\n";
		}
		expression+="result;";
		b.expression=expression;
		r.push(x);
		r.push(a);
	}
	return r;
}

function createTextDisplayEffect(){
	var settings=showSettingsDialog();
	if(settings===null)return;
	
	var jsonFile=File.openDialog("JSON dosyasını seçin","JSON:*.json");
	if(jsonFile===null){
		alert("Dosya seçilmedi.");
		return;
	}
	
	try{
		jsonFile.encoding="UTF-8";
		jsonFile.open("r");
		var jsonContent=jsonFile.read();
		jsonFile.close();
		
		if(!jsonContent || typeof jsonContent !== "string"){
			throw new Error("Geçersiz JSON içeriği");
		}
		
		var sentences=parseJSON(jsonContent);
		
		if(Object.prototype.toString.call(sentences) !== '[object Array]' || sentences.length===0){
			throw new Error("Geçerli cümle dizisi bulunamadı");
		}
		
		var comp=app.project.activeItem;
		if(!comp || !(comp instanceof CompItem)){
			throw new Error("Lütfen bir kompozisyon açın");
		}
		
		var textLayers=createPageBasedTextDisplay(comp,sentences,settings);
		alert("İşlem tamamlandı. "+textLayers.length+" sayfa oluşturuldu.");
		
	}catch(error){
		alert("Hata: "+error.message);
	}
}

createTextDisplayEffect();