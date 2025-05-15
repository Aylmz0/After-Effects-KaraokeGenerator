// After Effects için Gelişmiş Karaoke Efekti Scripti
// Bu script JSON dosyasından cümle zamanlamalarını alır
// ve ekranda sırayla gösterir - aktif cümle beyaz, öncekiler gri renkte kalır

// Yardımcı Fonksiyon: JavaScript dizesi için metni güvenli hale getirir
function escapeForJSStringLiteral(str) {
    if (typeof str !== 'string') {
        str = String(str);
    }
    return str
        .replace(/\\/g, '\\\\')  // 1. Ters eğik çizgileri kaçır (\\ -> \\\\)
        .replace(/"/g, '\\"')   // 2. Çift tırnakları kaçır (" -> \\")
        .replace(/\n/g, '\\n')  // 3. Yeni satırları kaçır (\n -> \\n)
        .replace(/\r/g, '\\r');  // 4. Satır başlarını kaçır (\r -> \\r)
}

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
    var fontSizeInput = fontSizeGroup.add("edittext", undefined, "30");
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
    var minCharsInput = minCharsGroup.add("edittext", undefined, "50");
    minCharsInput.characters = 5;

    var maxCharsGroup = sentenceGroup.add("group");
    maxCharsGroup.add("statictext", undefined, "Maksimum Karakter Sayısı:");
    var maxCharsInput = maxCharsGroup.add("edittext", undefined, "55");
    maxCharsInput.characters = 5;

    var maxCombineGapGroup = sentenceGroup.add("group");
    maxCombineGapGroup.add("statictext", undefined, "Maks. Birleştirme Aralığı (sn):");
    var maxCombineGapInput = maxCombineGapGroup.add("edittext", undefined, "3.0");
    maxCombineGapInput.characters = 5;

    // Ekran ayarları
    var screenGroup = dialog.add("panel", undefined, "Ekran Ayarları");
    screenGroup.orientation = "column";
    screenGroup.alignChildren = ["left", "top"];
    screenGroup.spacing = 5;
    screenGroup.margins = 10;

    var lineCountGroup = screenGroup.add("group");
    lineCountGroup.add("statictext", undefined, "Maksimum Satır Sayısı:");
    var maxLinesInput = lineCountGroup.add("edittext", undefined, "17");
    maxLinesInput.characters = 5;

    var minSilenceForNewPageGroup = screenGroup.add("group");
    minSilenceForNewPageGroup.add("statictext", undefined, "Yeni Sayfa İçin Min. Sessizlik (sn):");
    var minSilenceForNewPageInput = minSilenceForNewPageGroup.add("edittext", undefined, "3.0");
    minSilenceForNewPageInput.characters = 5;

    var pageEndBufferTimeGroup = screenGroup.add("group");
    pageEndBufferTimeGroup.add("statictext", undefined, "Sayfa Sonu Ek Süre (sn):");
    var pageEndBufferTimeInput = pageEndBufferTimeGroup.add("edittext", undefined, "0.5"); // Varsayılan 0.5 saniye
    pageEndBufferTimeInput.characters = 5;

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
    alignDropdown.selection = 1; // Varsayılan olarak Sol seçili

    var xPosGroup = posGroup.add("group");
    xPosGroup.add("statictext", undefined, "X Pozisyonu (%):");
    var xPosInput = posGroup.add("edittext", undefined, "10");
    xPosInput.characters = 5;

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
            maxChars: parseInt(maxCharsInput.text),
            maxCombineGap: parseFloat(maxCombineGapInput.text),
            maxLines: parseInt(maxLinesInput.text),
            minSilenceForNewPage: parseFloat(minSilenceForNewPageInput.text),
            pageEndBufferTime: parseFloat(pageEndBufferTimeInput.text),
            lineSpacing: parseInt(lineSpacingInput.text),
            alignment: alignDropdown.selection.index,
            xPosition: parseInt(xPosInput.text),
            yPosition: parseInt(yPosInput.text),
            animationType: animTypeDropdown.selection.index,
            animationSpeed: parseFloat(animSpeedInput.text) / 100
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

// Cümleleri birleştirme (Çift sınırlı versiyon)
function combineShortSentences(sentences, minChars, maxChars, maxCombineGap) {
    // Manuel trim fonksiyonu
    function trimString(str) {
        if (!str || typeof str !== "string") return "";
        while (str.length > 0 && (str.charAt(0) == " " || str.charAt(0) == "\n" || 
               str.charAt(0) == "\r" || str.charAt(0) == "\t")) {
            str = str.substring(1);
        }
        while (str.length > 0 && (str.charAt(str.length - 1) == " " || str.charAt(str.length - 1) == "\n" || 
               str.charAt(str.length - 1) == "\r" || str.charAt(str.length - 1) == "\t")) {
            str = str.substring(0, str.length - 1);
        }
        return str;
    }
    
    if (!sentences || sentences.length === 0) return [];
    
    var result = [];
    var currentSentence = null;
    
    for (var i = 0; i < sentences.length; i++) {
        var sentence = sentences[i];
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
             sentence.end = sentence.start + 1;
         }

        var trimmedText = trimString(sentence.text);
        var originalSentenceObject = { text: sentence.text, start: sentence.start, end: sentence.end }; // Keep original data

        if (currentSentence === null) {
            currentSentence = {
                text: sentence.text,
                start: sentence.start,
                end: sentence.end,
                length: trimmedText.length,
                originalSegments: [originalSentenceObject] // Initialize with the original sentence
            };
        } else {
            var timeDiff = (sentence.start !== undefined && currentSentence.end !== undefined) 
                ? Math.abs(currentSentence.end - sentence.start) 
                : 1.0;
                
            var potentialCombinedText = currentSentence.text + " " + sentence.text;
            var potentialCombinedLength = trimString(potentialCombinedText).length;
            
            // Güncelleme: Çok uzun zaman farklarında birleştirmeyi engelle
            // var MAX_INTER_SENTENCE_GAP_FOR_COMBINING = 7.0; // Saniye. Bu süreden daha uzun boşluklar birleştirmeyi engeller.

            var shouldCombine = false;
            // Sadece zaman farkı kabul edilebilir bir aralıktaysa birleştirmeyi değerlendir.
            if (timeDiff < maxCombineGap) { // maxCombineGap kullanıcı ayarından gelecek
                if (potentialCombinedLength <= maxChars) { // Ve maxChars'a uyuluyorsa
                    if (currentSentence.length < minChars) { // Mevcut cümle çok kısaysa birleştir
                        shouldCombine = true;
                    } else if (timeDiff < 0.5) { // Veya mevcut cümle yeterince uzunsa ama sonraki cümle çok yakınsa birleştir (0.5sn'den az farkla)
                        shouldCombine = true;
                    }
                }
            }
            
            if (shouldCombine) {
                var space = (currentSentence.text.length > 0 && sentence.text.length > 0) ? " " : "";
                currentSentence.text += space + sentence.text; // Birleşik metni güncelle
                currentSentence.end = sentence.end; // Bitiş zamanını güncelle
                currentSentence.length = trimString(currentSentence.text).length; // Uzunluğu güncelle
                currentSentence.originalSegments.push(originalSentenceObject); // Yeni orijinal parçayı ekle
            } else {
                currentSentence.text = trimString(currentSentence.text); // Son bir kez trim et
                if (currentSentence.text.length > 0) {
                    result.push(currentSentence);
                }
                currentSentence = { // Yeni bir `currentSentence` başlat
                    text: sentence.text,
                    start: sentence.start,
                    end: sentence.end,
                    length: trimmedText.length,
                    originalSegments: [originalSentenceObject]
                };
            }
        }
    }
    
    if (currentSentence !== null) {
        currentSentence.text = trimString(currentSentence.text); // Son bir kez trim et
        if (currentSentence.text.length > 0) {
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
    
    var pages = []; // Oluşturulan AE katmanlarını (sayfa başına 2) tutar
    var currentSentenceIndex = 0;
    var pageCounter = 0;

    while (currentSentenceIndex < sentences.length) {
        pageCounter++;
        var pageSentences = [];
        var pageStartTime = -1;
        var pageEndTime = -1;

        // Bu sayfa için cümleleri topla
        for (var i = 0; i < settings.maxLines && currentSentenceIndex < sentences.length; i++) {
            var nextSentence = sentences[currentSentenceIndex];
            if (pageSentences.length === 0) {
                pageSentences.push(nextSentence);
                pageStartTime = nextSentence.start;
                currentSentenceIndex++;
            } else {
                var lastSentenceOnPage = pageSentences[pageSentences.length - 1];
                var gap = nextSentence.start - lastSentenceOnPage.end;
                if (gap >= settings.minSilenceForNewPage) {
                    // Bu cümle yeni bir sayfa başlatmalı, mevcut döngüyü kır
                    break; 
                } else {
                    pageSentences.push(nextSentence);
                    currentSentenceIndex++;
                }
            }
        }

        if (pageSentences.length === 0) {
            // Bu durumun olmaması gerekir ama olursa sonsuz döngüyü engelle
            break;
        }

        // Sayfanın bitiş zamanını belirle
        pageEndTime = pageSentences[pageSentences.length - 1].end + settings.pageEndBufferTime;
        
        // Güvenlik: pageStartTime tanımsızsa veya hatalıysa düzelt (bu pek olası değil yeni mantıkla ama kalsın)
        if (pageStartTime === -1 && pageSentences.length > 0) {
             pageStartTime = pageSentences[0].start;
        }
        // Güvenlik: Eğer pageEndTime hala tanımsızsa veya pageStartTime'dan küçükse, düzelt
        if (pageEndTime <= pageStartTime && pageSentences.length > 0) {
            pageEndTime = pageSentences[pageSentences.length - 1].end + 2.0;
        }

        // --- Katman Oluşturma Mantığı (Bu kısım büyük ölçüde aynı kalacak) ---
        // Sadece pageCounter ve pageSentences'ı kullanacak şekilde adapte edilecek.
        // ... (Önceki inactiveLayer ve activeLayer oluşturma kodunuz buraya gelecek,
        //      pageIndex yerine pageCounter kullanılacak ve pageSentences doğrudan kullanılacak)
        // ... Örneğin: var inactiveLayerName = "Sayfa " + pageCounter + " - İnaktif";

        // --- İnaktif Metin Katmanı Oluşturma ---
        var inactiveLayer = comp.layers.addText("");
        var inactiveLayerName = "Sayfa " + pageCounter + " - İnaktif"; 
        inactiveLayer.name = inactiveLayerName;
        inactiveLayer.startTime = pageStartTime;
        inactiveLayer.outPoint = pageEndTime;

        var inactiveTextProp = inactiveLayer.property("ADBE Text Properties").property("ADBE Text Document");
        var inactiveTextDoc = inactiveTextProp.value;

        var fullPageText = "";
        for (var k = 0; k < pageSentences.length; k++) {
            if (pageSentences[k] && pageSentences[k].text) {
                fullPageText += pageSentences[k].text + "\n";
            }
        }
        if (fullPageText.length > 0) {
             fullPageText = fullPageText.substring(0, fullPageText.length - 1);
        }
        inactiveTextDoc.text = fullPageText;

        inactiveTextDoc.fontSize = settings.fontSize;
        var inactiveColorArray = [settings.inactiveFontColor[0]/255, settings.inactiveFontColor[1]/255, settings.inactiveFontColor[2]/255];
        inactiveTextDoc.fillColor = inactiveColorArray;
        inactiveTextDoc.leading = settings.fontSize * (settings.lineSpacing / 100);
        if (settings.alignment === 0) inactiveTextDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
        else if (settings.alignment === 1) inactiveTextDoc.justification = ParagraphJustification.LEFT_JUSTIFY;
        else inactiveTextDoc.justification = ParagraphJustification.RIGHT_JUSTIFY;
        inactiveTextProp.setValue(inactiveTextDoc);

        var inactiveTransform = inactiveLayer.property("ADBE Transform Group");
        var inactivePosition = inactiveTransform.property("ADBE Position");
        var xPos;
        if (settings.alignment === 0) xPos = comp.width / 2;
        else if (settings.alignment === 1) xPos = comp.width * (settings.xPosition / 100); // Yüzdeyi kullan
        else xPos = comp.width * (1 - (settings.xPosition / 100)); // Sağ için de yüzdeyi kullan
        var yPos = comp.height * (settings.yPosition / 100);
        inactivePosition.setValue([xPos, yPos]);
        inactiveTransform.property("ADBE Opacity").setValue(100);

        // --- Aktif Metin Katmanı Oluşturma ---
        var activeLayer = comp.layers.addText("");
        var activeLayerName = "Sayfa " + pageCounter + " - Aktif";
        activeLayer.name = activeLayerName;
        activeLayer.startTime = pageStartTime;
        activeLayer.outPoint = pageEndTime;
        
        var activeTextProp = activeLayer.property("ADBE Text Properties").property("ADBE Text Document");
        var activeTextDoc = activeTextProp.value;
        
        activeTextDoc.fontSize = settings.fontSize;
        var activeColorArray = [settings.activeFontColor[0]/255, settings.activeFontColor[1]/255, settings.activeFontColor[2]/255];
        activeTextDoc.fillColor = activeColorArray;
        activeTextDoc.leading = settings.fontSize * (settings.lineSpacing / 100);
        if (settings.alignment === 0) activeTextDoc.justification = ParagraphJustification.CENTER_JUSTIFY;
        else if (settings.alignment === 1) activeTextDoc.justification = ParagraphJustification.LEFT_JUSTIFY;
        else activeTextDoc.justification = ParagraphJustification.RIGHT_JUSTIFY;
        activeTextProp.setValue(activeTextDoc);
        
        var activeTransform = activeLayer.property("ADBE Transform Group");
        var activePosition = activeTransform.property("ADBE Position");
        activePosition.setValue([xPos, yPos]);
        
        var expression = "";
        expression += "var currentTime = time;\n";
        expression += "var result = \"\";\n\n";
        expression += "function animateText(text, startTime, endTime, currentTime, speedFactor) {\n";
        expression += "  var textLength = text.length;\n";
        expression += "  var duration = (endTime - startTime) / speedFactor;\n";
        expression += "  if (duration <= 0) return text;\n";
        expression += "  var charDuration = duration / textLength;\n";
        expression += "  if (charDuration <= 0) return text;\n";
        expression += "  var elapsed = currentTime - startTime;\n";
        expression += "  var visibleChars = Math.floor(elapsed / charDuration);\n";
        expression += "  visibleChars = Math.max(0, Math.min(textLength, visibleChars));\n";
        expression += "  return text.substring(0, visibleChars);\n";
        expression += "}\n\n";

        for (var j = 0; j < pageSentences.length; j++) {
            var currentLineData = pageSentences[j];
            if (!currentLineData || !currentLineData.text) continue;

            var lineSafeText = escapeForJSStringLiteral(currentLineData.text); // Bu zaten birleştirilmiş metin
            var lineStartTime = currentLineData.start;
            var lineEndTime = currentLineData.end;
            var lineBreak = (j < pageSentences.length - 1) ? "\\n" : "";
            
            expression += "if (currentTime >= " + lineStartTime + ") {\n";
            expression += "  if (currentTime < " + lineEndTime + ") {\n";
            
            if (settings.animationType === 0) { // Harf harf açılma
                expression += "      var lineDisplayText = '';\n";
                var segmentsArrString = "[";
                for (var k_seg = 0; k_seg < currentLineData.originalSegments.length; k_seg++) {
                    var seg = currentLineData.originalSegments[k_seg];
                    var escapedTextContent = escapeForJSStringLiteral(String(seg.text));
                    segmentsArrString += "{text: \"" + escapedTextContent + "\", start: " + seg.start + ", end: " + seg.end + "}";
                    if (k_seg < currentLineData.originalSegments.length - 1) {
                        segmentsArrString += ",";
                    }
                }
                segmentsArrString += "]";
                expression += "      var currentLineSegments = " + segmentsArrString + ";\n";
                expression += "      var builtUpTextForLine = '';\n";
                expression += "      for (var segIdx = 0; segIdx < currentLineSegments.length; segIdx++) {\n";
                expression += "        var segment = currentLineSegments[segIdx];\n";
                expression += "        var spacing = (segIdx > 0 && builtUpTextForLine.length > 0 && segment.text.length > 0) ? ' ' : '';\n"; 
                expression += "        if (currentTime >= segment.end) {\n";
                expression += "          builtUpTextForLine += spacing + segment.text;\n";
                expression += "        } else if (currentTime >= segment.start && currentTime < segment.end) {\n";
                expression += "          builtUpTextForLine += spacing;\n"; 
                expression += "          var animatedSegmentPart = animateText(segment.text, segment.start, segment.end, currentTime, " + settings.animationSpeed + ");\n";
                expression += "          builtUpTextForLine += animatedSegmentPart;\n";
                expression += "          break;\n";
                expression += "        } else {\n";
                expression += "          break;\n";
                expression += "        }\n";
                expression += "      }\n"; 
                expression += "      lineDisplayText = builtUpTextForLine;\n";
                expression += "      result += lineDisplayText + \"" + lineBreak + "\";\n";
            } else { // Anında görünme
                expression += "    result += \"" + lineSafeText + "\" + \"" + lineBreak + "\";\n";
            }
            expression += "  } else {\n";
            expression += "     result += \"" + lineSafeText + "\" + \"" + lineBreak + "\";\n";
            expression += "  }\n";
            expression += "}\n";
        }
        expression += "result;";
        activeTextProp.expression = expression;
        
        pages.push(inactiveLayer);
        pages.push(activeLayer);
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
        if (settings.minChars > 0 || settings.maxChars > 0) {
            sentences = combineShortSentences(sentences, settings.minChars, settings.maxChars, settings.maxCombineGap);
            alert("Cümleler " + settings.minChars + "-" + settings.maxChars + " karakter aralığına ve " + settings.maxCombineGap + "sn maksimum birleştirme aralığına göre birleştirildi. Yeni cümle sayısı: " + sentences.length);
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