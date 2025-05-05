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

    var minCharsGroup = sentenceGroup.add("group");
    minCharsGroup.add("statictext", undefined, "Minimum Karakter Sayısı:");
    var minCharsInput = minCharsGroup.add("edittext", undefined, "30");
    minCharsInput.characters = 5;

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
            minChars: parseInt(minCharsInput.text),
            maxLines: parseInt(maxLinesInput.text),
            lineSpacing: parseInt(lineSpacingInput.text),
            alignment: alignDropdown.selection.index,
            yPosition: parseInt(yPosInput.text),
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

// Cümleleri birleştirme (Karakter sayısına göre güncellendi)
function combineShortSentences(sentences, minChars) {
    // Manuel trim fonksiyonu
    function trimString(str) {
        if (!str || typeof str !== "string") return ""; // Added type check
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
    
    if (!sentences || sentences.length === 0) return [];
    
    var result = [];
    var currentSentence = null;
    var charCount = 0;
    // Define a max character limit to prevent overly long combined lines.
    // Use minChars * 2.5, but ensure it's at least minChars + 20.
    var maxCharLimit = Math.max(minChars + 20, Math.floor(minChars * 2.5));
    
    for (var i = 0; i < sentences.length; i++) {
        var sentence = sentences[i];
        // Ensure sentence object and text exist, provide defaults if not
        if (!sentence || typeof sentence !== 'object') {
             sentence = { text: "", start: 0, end: 0 };
        }
        if (typeof sentence.text !== 'string') {
            sentence.text = "";
        }
         if (typeof sentence.start !== 'number') {
             sentence.start = (currentSentence && typeof currentSentence.end === 'number') ? currentSentence.end : 0;
         }
         if (typeof sentence.end !== 'number') {
             sentence.end = sentence.start + 1; // Default 1 second duration if end time missing
         }

        
        // Use trimmed text for length calculation, but potentially keep original for combining
        var trimmedText = trimString(sentence.text);
        var currentChars = trimmedText.length;
        
        if (currentSentence === null) {
            // Start a new potential combined sentence
            currentSentence = {
                text: sentence.text, // Keep original text initially
                start: sentence.start,
                end: sentence.end
            };
            charCount = currentChars; // Use trimmed length for decision making
        } else {
            // Check timing difference, handle potential undefined times
            var timeDiff = (sentence.start !== undefined && currentSentence.end !== undefined) ? Math.abs(currentSentence.end - sentence.start) : 1.0; 

            // Tentatively combine text using original sentence text to preserve internal spacing if needed
            var potentialCombinedText = currentSentence.text + " " + sentence.text;
            var potentialCombinedLength = trimString(potentialCombinedText).length; // Check length of trimmed version

            // Conditions to combine:
            // 1. Current combined sentence's trimmed length is shorter than minChars.
            // 2. Time gap is small (< 0.5s).
            // 3. Combining does NOT exceed maxCharLimit (based on trimmed length).
            if (charCount < minChars &&
                timeDiff < 0.5 &&
                potentialCombinedLength <= maxCharLimit)
            {
                // Combine the sentences
                currentSentence.text = potentialCombinedText;
                // Use the end time of the newly added sentence
                currentSentence.end = sentence.end; 
                charCount = potentialCombinedLength; // Update character count to the new trimmed length
            } else {
                // Cannot combine. Push the previous combined sentence and start a new one.
                // Trim the text *before* pushing to result
                currentSentence.text = trimString(currentSentence.text);
                if (currentSentence.text.length > 0) { // Avoid pushing empty sentences
                     result.push(currentSentence);
                }

                // Start new sentence group with the current sentence
                currentSentence = {
                    text: sentence.text, // Keep original text initially
                    start: sentence.start,
                    end: sentence.end
                };
                charCount = currentChars; // Use trimmed length for decision making
            }
        }
    }
    
    // Push the last processed sentence group after trimming
    if (currentSentence !== null) {
        currentSentence.text = trimString(currentSentence.text);
         if (currentSentence.text.length > 0) { // Avoid pushing empty sentences
            result.push(currentSentence);
         }
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
        
        // --- İnaktif Metin Katmanı Oluşturma ---
        var inactiveLayer = comp.layers.addText("");
        var inactiveLayerName = "Sayfa " + (pageIndex + 1) + " - İnaktif"; // Ad değişti
        inactiveLayer.name = inactiveLayerName;
        inactiveLayer.startTime = pageStartTime;
        inactiveLayer.outPoint = pageEndTime;

        var inactiveTextProp = inactiveLayer.property("ADBE Text Properties").property("ADBE Text Document"); // Değişken adı değişti
        var inactiveTextDoc = inactiveTextProp.value; // Değişken adı değişti

        // İnaktif metnini oluştur (tüm cümleler birleşik)
        var fullPageText = "";
        for (var k = 0; k < pageSentences.length; k++) {
            if (pageSentences[k] && pageSentences[k].text) {
                fullPageText += pageSentences[k].text + "\n";
            }
        }
        // Sondaki newline karakterini kaldır
        if (fullPageText.length > 0) {
             fullPageText = fullPageText.substring(0, fullPageText.length - 1);
        }
        inactiveTextDoc.text = fullPageText;

        // İnaktif stil ayarları
        inactiveTextDoc.fontSize = settings.fontSize;
        var inactiveColorArray = [settings.inactiveFontColor[0]/255, settings.inactiveFontColor[1]/255, settings.inactiveFontColor[2]/255];
        inactiveTextDoc.fillColor = inactiveColorArray;
        inactiveTextDoc.leading = settings.fontSize * (settings.lineSpacing / 100);
        if (settings.alignment === 0) inactiveTextDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
        else if (settings.alignment === 1) inactiveTextDoc.justification = ParagraphJustification.LEFT_JUSTIFY;
        else inactiveTextDoc.justification = ParagraphJustification.RIGHT_JUSTIFY;
        inactiveTextProp.setValue(inactiveTextDoc);

        // İnaktif pozisyonu
        var inactiveTransform = inactiveLayer.property("ADBE Transform Group"); // Değişken adı değişti
        var inactivePosition = inactiveTransform.property("ADBE Position"); // Değişken adı değişti
        var xPos;
        if (settings.alignment === 0) xPos = comp.width / 2;
        else if (settings.alignment === 1) xPos = comp.width * 0.1;
        else xPos = comp.width * 0.9;
        var yPos = comp.height * (settings.yPosition / 100);
        inactivePosition.setValue([xPos, yPos]);

        // İnaktif opaklığı %100
        inactiveTransform.property("ADBE Opacity").setValue(100);

        // --- Aktif Metin Katmanı Oluşturma ---
        var activeLayer = comp.layers.addText(""); // Değişken adı değişti
        var activeLayerName = "Sayfa " + (pageIndex + 1) + " - Aktif"; // Ad değişti
        activeLayer.name = activeLayerName;
        
        // Zamanlama (İnaktif ile aynı)
        activeLayer.startTime = pageStartTime;
        activeLayer.outPoint = pageEndTime;
        
        // Aktif metin belgesini al
        var activeTextProp = activeLayer.property("ADBE Text Properties").property("ADBE Text Document"); // Değişken adı değişti
        var activeTextDoc = activeTextProp.value; // Değişken adı değişti
        
        // Aktif stil ayarları
        activeTextDoc.fontSize = settings.fontSize;
        var activeColorArray = [settings.activeFontColor[0]/255, settings.activeFontColor[1]/255, settings.activeFontColor[2]/255]; // Aktif renk burada tanımlandı
        activeTextDoc.fillColor = activeColorArray;
        activeTextDoc.leading = settings.fontSize * (settings.lineSpacing / 100); // Satır aralığı
        // Hizalama ayarları
        if (settings.alignment === 0) activeTextDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
        else if (settings.alignment === 1) activeTextDoc.justification = ParagraphJustification.LEFT_JUSTIFY;
        else activeTextDoc.justification = ParagraphJustification.RIGHT_JUSTIFY;
        
        activeTextProp.setValue(activeTextDoc);
        
        // Pozisyonu ayarla (İnaktif ile aynı)
        var activeTransform = activeLayer.property("ADBE Transform Group"); // Değişken adı değişti
        var activePosition = activeTransform.property("ADBE Position"); // Değişken adı değişti
        activePosition.setValue([xPos, yPos]);
        
        // Expression oluştur - Sadece animasyonlu metin (Slider yok)
        var expression = "";
        expression += "var currentTime = time;\n";
        expression += "var result = \"\";\n\n";
        expression += "// Metni harf harf açma fonksiyonu\n";
        expression += "function animateText(text, startTime, endTime, currentTime, speedFactor) {\n";
        expression += "  var textLength = text.length;\n";
        expression += "  var duration = (endTime - startTime) / speedFactor;\n";
        expression += "  if (duration <= 0) return text; // Prevent division by zero and handle zero duration\n";
        expression += "  var charDuration = duration / textLength;\n";
        expression += "  if (charDuration <= 0) return text; // Prevent division by zero for charDuration\n";
        expression += "  var elapsed = currentTime - startTime;\n";
        expression += "  var visibleChars = Math.floor(elapsed / charDuration);\n";
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
            var lineBreak = (i < pageSentences.length - 1) ? "\\n" : ""; // Son cümleden sonra satır atlama

            // Her cümle için koşullu ifade
            expression += "if (currentTime >= " + startTime + ") {\n";
            
            // Aktif veya inaktif olma durumu (Burada hep aktif olacak, renk değişimi yok)
            expression += "  if (currentTime < " + endTime + ") { // Aktif görünüm süresi\n";
            
            // Animasyon tipi kontrolü
            if (settings.animationType === 0) { // Harf harf açılma
                expression += "    var displayText = animateText(\"" + safeText + "\", " + startTime + ", " + endTime + ", currentTime, " + settings.animationSpeed + ");\n";
                expression += "    result += displayText + \"" + lineBreak + "\";\n"; // Sadece aktif metni ekle
            } else { // Anında görünme
                expression += "    result += \"" + safeText + "\" + \"" + lineBreak + "\";\n"; // Sadece aktif metni ekle
            }
            expression += "  } else { // Cümle bitti, inaktif katman gösterecek\n";
            expression += "     result += \"" + safeText + "\" + \"" + lineBreak + "\";\n"; // Biten cümleyi de göster (arkada inaktif görünecek)
            expression += "  }\n";
            expression += "}\n";
        }
        
        expression += "result; // Sonuç olarak animasyonlu aktif metni göster";
        
        // Expression'ı uygula
        activeTextProp.expression = expression;
        
        // Katmanları listeye ekle (İnaktif ve Aktif)
        pages.push(inactiveLayer); 
        pages.push(activeLayer); 
    }
    
    return pages; // İnaktif ve Aktif katmanları döndürür
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
        if (settings.minChars > 0) {
            sentences = combineShortSentences(sentences, settings.minChars);
            alert("Cümleler minimum " + settings.minChars + " karaktere göre birleştirildi. Yeni cümle sayısı: " + sentences.length);
        }
        
        // Aktif kompozisyonu al
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) {
            alert("Lütfen bir kompozisyon açın.");
            return;
        }
        
        // Sayfa bazlı metin gösterimi oluştur
        var textLayers = createPageBasedTextDisplay(comp, sentences, settings);
        
        alert("İşlem tamamlandı. " + textLayers.length + " sayfa oluşturuldu.");
        
    } catch (error) {
        alert("Hata: " + error.message);
    }
}

// Scripti çalıştır
createTextDisplayEffect();