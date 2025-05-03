// After Effects için Gelişmiş Karaoke Efekti Scripti
// Bu script JSON dosyasından cümle zamanlamalarını alır
// ve ekranda sırayla gösterir - aktif cümle beyaz, öncekiler gri renkte kalır

// Manuel JSON ayrıştırma fonksiyonu - ExtendScript JSON.parse alternatifi
function parseJSON(text) {
    try {
        // Eğer eval aracılığıyla parse etmek mümkünse
        return eval("(" + text + ")");
    } catch (e) {
        // Eval başarısız olursa daha güvenli bir yöntem dene
        try {
            // Standart JSON.parse'ı dene
            return JSON.parse(text);
        } catch (e2) {
            throw new Error("JSON ayrıştırılamadı: " + e2.message);
        }
    }
}

// Kullanıcı ayarları penceresi
function showSettingsDialog() {
    var dialog = new Window("dialog", "Metin Gösterici Ayarları");
    dialog.orientation = "column";
    dialog.alignChildren = ["left", "top"];
    dialog.spacing = 10;
    dialog.margins = 16;
    
    // Animasyon tipi seçimi
    var animationGroup = dialog.add("panel", undefined, "Animasyon Ayarları");
    animationGroup.orientation = "column";
    animationGroup.alignChildren = ["left", "top"];
    animationGroup.spacing = 5;
    animationGroup.margins = 10;
    
    var animTypeGroup = animationGroup.add("group");
    animTypeGroup.add("statictext", undefined, "Animasyon Tipi:");
    var animTypeDropdown = animTypeGroup.add("dropdownlist", undefined, ["Harf Harf Açılma", "Anında Görünme"]);
    animTypeDropdown.selection = 0; // Varsayılan olarak harf harf açılma seçili
    
    var animSpeedGroup = animationGroup.add("group");
    animSpeedGroup.add("statictext", undefined, "Animasyon Hızı (%):");
    var animSpeedInput = animSpeedGroup.add("edittext", undefined, "100");
    animSpeedInput.characters = 5;
    
    // Hız açıklaması
    var speedDesc = animationGroup.add("statictext", undefined, "Not: 100% standart hız, 50% yavaş, 200% hızlı");
    speedDesc.graphics.font = ScriptUI.newFont(speedDesc.graphics.font.name, ScriptUI.FontStyle.ITALIC, 10);

    // Font ayarları
    var fontGroup = dialog.add("panel", undefined, "Font Ayarları");
    fontGroup.orientation = "column";
    fontGroup.alignChildren = ["left", "top"];
    fontGroup.spacing = 5;
    fontGroup.margins = 10;

    var fontSizeGroup = fontGroup.add("group");
    fontSizeGroup.add("statictext", undefined, "Font Boyutu:");
    var fontSizeInput = fontSizeGroup.add("edittext", undefined, "40");
    fontSizeInput.characters = 5;

    var activeFontColorGroup = fontGroup.add("group");
    activeFontColorGroup.add("statictext", undefined, "Aktif Metin Rengi (R,G,B):");
    var activeFontColorInput = activeFontColorGroup.add("edittext", undefined, "255,255,255");
    activeFontColorInput.characters = 10;

    var inactiveFontColorGroup = fontGroup.add("group");
    inactiveFontColorGroup.add("statictext", undefined, "İnaktif Metin Rengi (R,G,B):");
    var inactiveFontColorInput = inactiveFontColorGroup.add("edittext", undefined, "100,100,100");
    inactiveFontColorInput.characters = 10;

    // Cümle ayarları (YENİ)
    var sentenceGroup = dialog.add("panel", undefined, "Cümle Ayarları");
    sentenceGroup.orientation = "column";
    sentenceGroup.alignChildren = ["left", "top"];
    sentenceGroup.spacing = 5;
    sentenceGroup.margins = 10;

    var minWordsGroup = sentenceGroup.add("group");
    minWordsGroup.add("statictext", undefined, "Minimum Kelime Sayısı:");
    var minWordsInput = minWordsGroup.add("edittext", undefined, "5");
    minWordsInput.characters = 5;

    // Ekran ayarları
    var screenGroup = dialog.add("panel", undefined, "Ekran Ayarları");
    screenGroup.orientation = "column";
    screenGroup.alignChildren = ["left", "top"];
    screenGroup.spacing = 5;
    screenGroup.margins = 10;

    var lineCountGroup = screenGroup.add("group");
    lineCountGroup.add("statictext", undefined, "Maksimum Satır Sayısı:");
    var maxLinesInput = lineCountGroup.add("edittext", undefined, "10");
    maxLinesInput.characters = 5;

    var lineSpacingGroup = screenGroup.add("group");
    lineSpacingGroup.add("statictext", undefined, "Satır Aralığı (%):");
    var lineSpacingInput = lineSpacingGroup.add("edittext", undefined, "120");
    lineSpacingInput.characters = 5;

    // Pozisyon ayarları
    var posGroup = dialog.add("panel", undefined, "Pozisyon Ayarları");
    posGroup.orientation = "column";
    posGroup.alignChildren = ["left", "top"];
    posGroup.spacing = 5;
    posGroup.margins = 10;

    var alignGroup = posGroup.add("group");
    alignGroup.add("statictext", undefined, "Hizalama:");
    var alignDropdown = alignGroup.add("dropdownlist", undefined, ["Ortala", "Sol", "Sağ"]);
    alignDropdown.selection = 0;

    var yPosGroup = posGroup.add("group");
    yPosGroup.add("statictext", undefined, "Y Pozisyonu (%):");
    var yPosInput = posGroup.add("edittext", undefined, "10");
    yPosInput.characters = 5;

    // Arkaplan ayarları
    var bgGroup = dialog.add("panel", undefined, "Arkaplan Ayarları");
    bgGroup.orientation = "column";
    bgGroup.alignChildren = ["left", "top"];
    bgGroup.spacing = 5;
    bgGroup.margins = 10;

    var bgColorGroup = bgGroup.add("group");
    bgColorGroup.add("statictext", undefined, "Arkaplan Rengi (R,G,B):");
    var bgColorInput = bgColorGroup.add("edittext", undefined, "0,0,0");
    bgColorInput.characters = 10;

    var bgOpacityGroup = bgGroup.add("group");
    bgOpacityGroup.add("statictext", undefined, "Arkaplan Opaklığı (%):");
    var bgOpacityInput = bgOpacityGroup.add("edittext", undefined, "100");
    bgOpacityInput.characters = 5;

    // Butonlar
    var buttonGroup = dialog.add("group");
    buttonGroup.alignment = "center";
    var okButton = buttonGroup.add("button", undefined, "Tamam", {name: "ok"});
    var cancelButton = buttonGroup.add("button", undefined, "İptal", {name: "cancel"});

    var result = dialog.show();
    
    if (result == 1) {
        return {
            fontSize: parseInt(fontSizeInput.text),
            activeFontColor: parseColor(activeFontColorInput.text),
            inactiveFontColor: parseColor(inactiveFontColorInput.text),
            minWords: parseInt(minWordsInput.text),
            maxLines: parseInt(maxLinesInput.text),
            lineSpacing: parseInt(lineSpacingInput.text),
            alignment: alignDropdown.selection.index,
            yPosition: parseInt(yPosInput.text),
            bgColor: parseColor(bgColorInput.text),
            bgOpacity: parseInt(bgOpacityInput.text),
            animationType: animTypeDropdown.selection.index, // 0: Harf Harf, 1: Anında
            animationSpeed: parseFloat(animSpeedInput.text) / 100 // 1.0 = %100 hız, 0.5 = %50 hız
        };
    } else {
        return null;
    }
}

// RGB renk stringini ayrıştırma
function parseColor(colorStr) {
    var parts = colorStr.split(",");
    if (parts.length != 3) {
        return [255, 255, 255];
    }
    
    // Manuel olarak boşlukları temizle
    function trimString(str) {
        // Baştaki boşlukları temizle
        while (str.charAt(0) == " ") {
            str = str.substring(1);
        }
        // Sondaki boşlukları temizle
        while (str.charAt(str.length - 1) == " ") {
            str = str.substring(0, str.length - 1);
        }
        return str;
    }
    
    return [
        parseInt(trimString(parts[0])),
        parseInt(trimString(parts[1])),
        parseInt(trimString(parts[2]))
    ];
}

// Arkaplan oluşturma
function createBackgroundLayer(comp, settings) {
    var solidLayer = comp.layers.addSolid(
        [settings.bgColor[0]/255, settings.bgColor[1]/255, settings.bgColor[2]/255],
        "Arkaplan",
        comp.width,
        comp.height,
        1
    );
    
    // En alta gönder
    solidLayer.moveToEnd();
    
    // Opaklık ayarla
    var opacity = solidLayer.property("ADBE Transform Group").property("ADBE Opacity");
    opacity.setValue(settings.bgOpacity);
    
    return solidLayer;
}

// Cümleleri birleştirme (YENİ)
function combineShortSentences(sentences, minWords) {
    if (!sentences || sentences.length === 0) return [];
    
    // Manuel trim fonksiyonu
    function trimString(str) {
        // Baştaki boşlukları temizle
        while (str && str.charAt(0) == " ") {
            str = str.substring(1);
        }
        // Sondaki boşlukları temizle
        while (str && str.length > 0 && str.charAt(str.length - 1) == " ") {
            str = str.substring(0, str.length - 1);
        }
        return str;
    }
    
    var result = [];
    var currentSentence = null;
    var wordCount = 0;
    
    for (var i = 0; i < sentences.length; i++) {
        var sentence = sentences[i];
        // text değeri olmayan cümleleri kontrol et
        if (!sentence.text) {
            sentence.text = "";
        }
        
        // trim kullanmak yerine kendi fonksiyonumuzu kullanalım
        var trimmedText = trimString(sentence.text);
        var words = trimmedText.split(/\s+/);
        
        if (currentSentence === null) {
            currentSentence = {
                text: sentence.text,
                start: sentence.start,
                end: sentence.end
            };
            wordCount = words.length;
        } else {
            // Eğer yeterli kelime sayısına ulaşılmadıysa ve mevcut cümlenin sonraki cümle ile zamanı uyuşuyorsa
            if (wordCount < minWords && Math.abs(currentSentence.end - sentence.start) < 0.5) {
                currentSentence.text += " " + sentence.text;
                currentSentence.end = sentence.end;
                wordCount += words.length;
            } else {
                // Mevcut cümleyi ekle ve yeni bir cümleye başla
                result.push(currentSentence);
                currentSentence = {
                    text: sentence.text,
                    start: sentence.start,
                    end: sentence.end
                };
                wordCount = words.length;
            }
        }
    }
    
    // Son cümleyi ekle
    if (currentSentence !== null) {
        result.push(currentSentence);
    }
    
    return result;
}

// Sayfa bazlı metin gösterimi yaratma
function createPageBasedTextDisplay(comp, sentences, settings) {
    // Null veya boş sentences array kontrolü
    if (!sentences || sentences.length === 0) {
        alert("İşlenecek cümle bulunamadı!");
        return [];
    }
    
    // Maksimum sayfa sayısını hesapla
    var totalSentences = sentences.length;
    var sentencesPerPage = settings.maxLines;
    var totalPages = Math.ceil(totalSentences / sentencesPerPage);
    
    var pages = [];
    
    // Her sayfa için
    for (var pageIndex = 0; pageIndex < totalPages; pageIndex++) {
        var startIdx = pageIndex * sentencesPerPage;
        var endIdx = Math.min((pageIndex + 1) * sentencesPerPage, totalSentences);
        var pageSentences = sentences.slice(startIdx, endIdx);
        
        // Boş sayfa kontrolü
        if (pageSentences.length === 0) {
            continue;
        }
        
        // Sayfa katmanı oluştur
        var pageLayer = comp.layers.addText("");
        pageLayer.name = "Sayfa " + (pageIndex + 1);
        
        // Katman zamanlamalarını hesapla (Null kontrollü)
        if (!pageSentences[0] || pageSentences[0].start === undefined) {
            alert("Sayfa " + (pageIndex + 1) + " için başlangıç zamanı bulunamadı!");
            continue;
        }
        
        var pageStartTime = pageSentences[0].start;
        var pageEndTime;
        
        if (pageIndex < totalPages - 1 && sentences[endIdx] && sentences[endIdx].start !== undefined) {
            pageEndTime = sentences[endIdx].start; // Sonraki sayfanın başlangıcı
        } else if (pageSentences[pageSentences.length - 1] && 
                   pageSentences[pageSentences.length - 1].end !== undefined) {
            pageEndTime = pageSentences[pageSentences.length - 1].end + 2; // Son sayfanın sonu
        } else {
            pageEndTime = pageStartTime + 10; // Fallback değer
        }
        
        pageLayer.startTime = pageStartTime;
        pageLayer.outPoint = pageEndTime;
        
        // Metin belgesini al
        var textProp = pageLayer.property("ADBE Text Properties").property("ADBE Text Document");
        var textDoc = textProp.value;
        
        // Stil ayarları
        textDoc.fontSize = settings.fontSize;
        textDoc.fillColor = [settings.activeFontColor[0]/255, settings.activeFontColor[1]/255, settings.activeFontColor[2]/255];
        textDoc.leading = settings.fontSize * (settings.lineSpacing / 100); // Satır aralığı
        
        // Hizalama ayarları
        if (settings.alignment === 0) { // Ortala
            textDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
        } else if (settings.alignment === 1) { // Sol
            textDoc.justification = ParagraphJustification.LEFT_JUSTIFY;
        } else { // Sağ
            textDoc.justification = ParagraphJustification.RIGHT_JUSTIFY;
        }
        
        textProp.setValue(textDoc);
        
        // Pozisyonu ayarla
        var transform = pageLayer.property("ADBE Transform Group");
        var position = transform.property("ADBE Position");
        
        var xPos;
        if (settings.alignment === 0) { // Ortala
            xPos = comp.width / 2;
        } else if (settings.alignment === 1) { // Sol
            xPos = comp.width * 0.1;
        } else { // Sağ
            xPos = comp.width * 0.9;
        }
        var yPos = comp.height * (settings.yPosition / 100);
        
        position.setValue([xPos, yPos]);
        
        // Expression oluştur - HARF HARF AÇILMA EKLENDİ
        var expression = "";
        
        // Aktif ve inaktif renkler
        var activeColorArray = [settings.activeFontColor[0]/255, settings.activeFontColor[1]/255, settings.activeFontColor[2]/255];
        var inactiveColorArray = [settings.inactiveFontColor[0]/255, settings.inactiveFontColor[1]/255, settings.inactiveFontColor[2]/255];
        
        // Basit bir ifade oluştur - her zaman aktif cümle için beyaz, inaktif için gri
        expression += "var currentTime = time;\n";
        expression += "var result = \"\";\n\n";
        expression += "// Metni harf harf açma fonksiyonu\n";
        expression += "function animateText(text, startTime, endTime, currentTime, speedFactor) {\n";
        expression += "  var textLength = text.length;\n";
        expression += "  var duration = (endTime - startTime) / speedFactor;\n";
        expression += "  var charDuration = duration / textLength;\n";
        expression += "  var visibleChars = Math.floor((currentTime - startTime) * speedFactor / charDuration * textLength);\n";
        expression += "  visibleChars = Math.max(0, Math.min(textLength, visibleChars));\n";
        expression += "  return text.substring(0, visibleChars);\n";
        expression += "}\n\n";
        
        // Her cümle için ayrı ifadeler oluştur
        for (var i = 0; i < pageSentences.length; i++) {
            // Boş kontrolü
            if (!pageSentences[i] || !pageSentences[i].text) continue;
            
            // Metni temizle ve güvenli hale getir
            var safeText = "";
            try {
                safeText = String(pageSentences[i].text).replace(/"/g, '\\"').replace(/\n/g, '\\n');
            } catch (e) {
                safeText = "Metin hatası";
            }
            
            var startTime = pageSentences[i].start || 0;
            var endTime = pageSentences[i].end || (startTime + 5);
            
            // Her cümle için koşullu ifade
            expression += "if (currentTime >= " + startTime + ") {\n";
            
            // Aktif veya inaktif olma durumu
            expression += "  if (currentTime < " + endTime + ") {\n";
            
            // Animasyon tipi kontrolü
            if (settings.animationType === 0) { // Harf harf açılma
                // speedFactor parametresi eklendi
                expression += "    var displayText = animateText(\"" + safeText + "\", " + startTime + ", " + endTime + ", currentTime, " + settings.animationSpeed + ");\n";
                expression += "    result += displayText + \"\\n\";\n";
            } else { // Anında görünme
                expression += "    result += \"" + safeText + "\\n\";\n";
            }
            
            expression += "    text.sourceText.style.fillColor = [" + 
                         activeColorArray[0] + ", " + 
                         activeColorArray[1] + ", " + 
                         activeColorArray[2] + "];\n";
            expression += "  } else {\n";
            // İnaktif cümle - tam göster
            expression += "    result += \"" + safeText + "\\n\";\n";
            expression += "    text.sourceText.style.fillColor = [" + 
                         inactiveColorArray[0] + ", " + 
                         inactiveColorArray[1] + ", " + 
                         inactiveColorArray[2] + "];\n";
            expression += "  }\n";
            expression += "}\n";
        }
        
        expression += "result;";
        
        // Expression'ı uygula
        textProp.expression = expression;
        
        pages.push(pageLayer);
    }
    
    return pages;
}

// Ana işlev
function createTextDisplayEffect() {
    // Kullanıcı ayarlarını al
    var settings = showSettingsDialog();
    if (settings === null) {
        return; // Kullanıcı iptal etti
    }

    // JSON dosyasını seç
    var jsonFile = File.openDialog("JSON dosyasını seçin", "JSON:*.json");
    if (jsonFile === null) {
        alert("Dosya seçilmedi.");
        return;
    }

    try {
        // Dosyayı aç ve içeriği oku
        jsonFile.open("r");
        var jsonContent = jsonFile.read();
        jsonFile.close();
        
        alert("JSON dosyası okundu. İçerik uzunluğu: " + jsonContent.length + " karakter");
        
        // Manuel olarak boşlukları temizle
        function trimString(str) {
            if (!str || typeof str !== "string") return "";
            
            // Baştaki boşlukları temizle
            while (str.length > 0 && (str.charAt(0) == " " || str.charAt(0) == "\n" || 
                   str.charAt(0) == "\r" || str.charAt(0) == "\t")) {
                str = str.substring(1);
            }
            // Sondaki boşlukları temizle
            while (str.length > 0 && (str.charAt(str.length - 1) == " " || str.charAt(str.length - 1) == "\n" || 
                   str.charAt(str.length - 1) == "\r" || str.charAt(str.length - 1) == "\t")) {
                str = str.substring(0, str.length - 1);
            }
            return str;
        }
        
        jsonContent = trimString(jsonContent);
        
        // JSON içeriğini ayrıştır
        var sentences;
        try {
            // Özel parseJSON fonksiyonu kullanarak JSON'ı ayrıştır
            sentences = parseJSON(jsonContent);
            
            if (!sentences || !sentences.length) {
                alert("Cümle bulunamadı veya JSON biçimi hatalı.");
                return;
            }
            
            alert("JSON başarıyla ayrıştırıldı. " + sentences.length + " cümle bulundu.");
        } catch (error) {
            alert("JSON ayrıştırma hatası: " + error.message);
            return;
        }
        
        // Kısa cümleleri birleştir
        if (settings.minWords > 1) {
            sentences = combineShortSentences(sentences, settings.minWords);
            alert("Cümleler birleştirildi. Yeni cümle sayısı: " + sentences.length);
        }
        
        // Aktif kompozisyonu al
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) {
            alert("Lütfen bir kompozisyon açın.");
            return;
        }
        
        // Arkaplan katmanı oluştur
        createBackgroundLayer(comp, settings);
        
        // Sayfa bazlı metin gösterimi oluştur
        var textLayers = createPageBasedTextDisplay(comp, sentences, settings);
        
        alert("İşlem tamamlandı. " + textLayers.length + " sayfa oluşturuldu.");
        
    } catch (error) {
        alert("Hata: " + error.message);
    }
}

// Scripti çalıştır
createTextDisplayEffect();