// After Effects için Gelişmiş Karaoke Efekti Scripti
// Bu script SRT dosyasından cümle zamanlamalarını alır
// ve ekranda sırayla gösterir - aktif cümle beyaz, öncekiler gri renkte kalır

// Hata yönetimi için yardımcı fonksiyonlar
var debugLog = [];
var errorLog = [];

function logDebug(message) {
    debugLog.push(message);
    $.writeln("[DEBUG] " + message); // Konsola çıktı 
}

function logError(message) {
    var errorMsg = "[HATA] " + message;
    errorLog.push(errorMsg);
    $.writeln(errorMsg); // Konsola çıktı
}

function showError(title, message) {
    var detailedMessage = message + "\n\n" + getErrorReport();
    
    // Hata bilgilerini içeren bir diyalog göster
    var errorDialog = new Window("dialog", "Hata Raporu");
    errorDialog.orientation = "column";
    errorDialog.alignChildren = ["fill", "top"];
    errorDialog.spacing = 10;
    errorDialog.margins = 16;
    
    // Başlık
    var titleText = errorDialog.add("statictext", undefined, title);
    titleText.graphics.font = ScriptUI.newFont(titleText.graphics.font.name, ScriptUI.FontStyle.BOLD, 14);

    // Mesaj alanı (kaydırılabilir)
    var messageGroup = errorDialog.add("group");
    messageGroup.orientation = "column";
    messageGroup.alignChildren = ["fill", "top"];
    messageGroup.spacing = 5;
    messageGroup.maximumSize.height = 300;
    
    var messagePanel = messageGroup.add("panel");
    messagePanel.text = "Hata Detayları";
    
    var messageText = messagePanel.add("edittext", undefined, detailedMessage, {multiline: true, readonly: true});
    messageText.maximumSize.width = 450;
    messageText.maximumSize.height = 200;

    // Butonlar
    var buttonGroup = errorDialog.add("group");
    buttonGroup.alignment = "center";
    
    var copyButton = buttonGroup.add("button", undefined, "Hatayı Kopyala");
    var closeButton = buttonGroup.add("button", undefined, "Kapat", {name: "ok"});
    
    copyButton.onClick = function() {
        messageText.active = true;
        messageText.selectAll();
        app.executeCommand(app.findMenuCommandId("Copy"));
        alert("Hata bilgisi panoya kopyalandı!");
    };
    
    errorDialog.show();
}

function getErrorReport() {
    var report = "=== HATA RAPORU ===\n";
    report += "Tarih: " + new Date().toString() + "\n\n";
    
    report += "--- HATALAR ---\n";
    for (var i = 0; i < errorLog.length; i++) {
        report += errorLog[i] + "\n";
    }
    
    report += "\n--- DEBUG BİLGİLERİ ---\n";
    for (var i = 0; i < debugLog.length; i++) {
        report += debugLog[i] + "\n";
    }
    
    return report;
}

// YENİ: Sarılmamış metin indekslerini sarılmış metin indekslerine eşleyen yardımcı fonksiyon
function mapIndices(unwrappedText, wrappedText) {
    var map = [];
    var unwrappedIdx = 0;
    var wrappedIdx = 0;

    while (unwrappedIdx < unwrappedText.length && wrappedIdx < wrappedText.length) {
        var wrappedChar = wrappedText[wrappedIdx];
        var unwrappedChar = unwrappedText[unwrappedIdx];

        if (wrappedChar === unwrappedChar) {
            // Karakterler eşleşiyor, eşlemeyi yap
            map[unwrappedIdx] = wrappedIdx;
            unwrappedIdx++;
            wrappedIdx++;
        } else if (wrappedChar === '\n' || wrappedChar === '\r') {
            // Sarılmış metinde satır sonu var, sarılmış indeksi ilerlet
            // Mevcut sarılmamış indeks bir sonraki eşleşen karaktere eşlenecek
            wrappedIdx++;
        } else {
            // Beklenmeyen uyuşmazlık (örn. boşluk normalleştirme farkı?)
            // Güvenlik için eşleşmiş gibi kabul edip ilerle
            logDebug("Index mapping mismatch warning: unwrapped[" + unwrappedIdx + "]=" + unwrappedChar + ", wrapped[" + wrappedIdx + "]=" + wrappedChar);
            map[unwrappedIdx] = wrappedIdx;
            unwrappedIdx++;
            wrappedIdx++;
        }
    }
    // Kalan sarılmamış indeksleri sarılmış metnin sonuna eşle
    while (unwrappedIdx <= unwrappedText.length) { // <= unwrappedText.length son indeksi de (metnin sonu) eklemek için
         map[unwrappedIdx] = wrappedText.length; 
         unwrappedIdx++;
    }

    logDebug("Index map created. Length: " + map.length + ", Last mapped index: " + (map.length > 0 ? map[map.length-1] : 'N/A'));
    return map;
}

// Manuel JSON ayrıştırma fonksiyonu - ExtendScript JSON.parse alternatifi - KALDIRILDI
/*
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
*/

// Zaman damgasını saniyeye çevirme
function srtTimeToSeconds(timeStr) {
    var parts = timeStr.split(':');
    var hours = parseInt(parts[0], 10);
    var minutes = parseInt(parts[1], 10);
    var secondsAndMillis = parts[2].split(',');
    var seconds = parseInt(secondsAndMillis[0], 10);
    var milliseconds = parseInt(secondsAndMillis[1], 10);
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
}

// SRT dosyasını ayrıştırma fonksiyonu
function parseSRT(srtContent) {
    var lines = srtContent.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n\n');
    var sentences = [];
    for (var i = 0; i < lines.length; i++) {
        var block = lines[i].split('\n');
        if (block.length >= 3) {
            // İlk satır numara, onu atla
            // İkinci satır zaman damgası
            var timeParts = block[1].split(' --> ');
            if (timeParts.length === 2) {
                var startTime = srtTimeToSeconds(timeParts[0]);
                var endTime = srtTimeToSeconds(timeParts[1]);
                
                // Kalan satırlar metin
                var textLines = block.slice(2);
                // Metni normalleştir: satır sonlarını boşluğa çevir, çoklu boşlukları teke indir, baş/son boşlukları sil
                var text = textLines.join(' ').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, ''); 

                if (text) { // Boş metinleri ekleme
                    sentences.push({
                        text: text,
                        start: startTime,
                        end: endTime
                    });
                }
            }
        }
    }
    return sentences;
}

// Manuel olarak boşlukları temizle (Global hale getirildi)
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

    // YENİ: Kare Hızı Ayarı
    var frameRateGroup = animationGroup.add("group");
    frameRateGroup.add("statictext", undefined, "Kare Hızı (fps):");
    var frameRateInput = frameRateGroup.add("edittext", undefined, "30"); // Varsayılan 30 fps
    frameRateInput.characters = 5;
    var frameRateDesc = animationGroup.add("statictext", undefined, "Not: İfadenin doğru çalışması için kompozisyon kare hızıyla eşleşmelidir.");
    frameRateDesc.graphics.font = ScriptUI.newFont(frameRateDesc.graphics.font.name, ScriptUI.FontStyle.ITALIC, 10);

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

    // Cümle ayarları
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
    
    // YENİ: Maksimum Karakter Aşım Toleransı
    var maxCharToleranceGroup = sentenceGroup.add("group");
    maxCharToleranceGroup.add("statictext", undefined, "Maksimum Karakter Aşım Toleransı (%):");
    var maxCharToleranceInput = maxCharToleranceGroup.add("edittext", undefined, "10");
    maxCharToleranceInput.characters = 5;

    // Ekran ayarları
    var screenGroup = dialog.add("panel", undefined, "Ekran Ayarları");
    screenGroup.orientation = "column";
    screenGroup.alignChildren = ["left", "top"];
    screenGroup.spacing = 5;
    screenGroup.margins = 10;

    var lineCountGroup = screenGroup.add("group");
    lineCountGroup.add("statictext", undefined, "Maksimum Satır Sayısı:");
    var maxLinesInput = lineCountGroup.add("edittext", undefined, "20");
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
    alignDropdown.selection = 1; // Varsayılan olarak Sol seçili

    var xPosGroup = posGroup.add("group");
    xPosGroup.add("statictext", undefined, "X Pozisyonu (Sol Kenar %):");
    var xPosInput = xPosGroup.add("edittext", undefined, "10");
    xPosInput.characters = 5;

    var yPosGroup = posGroup.add("group");
    yPosGroup.add("statictext", undefined, "Y Pozisyonu (Üst Kenar %):");
    var yPosInput = yPosGroup.add("edittext", undefined, "10");
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
            maxCharTolerance: parseInt(maxCharToleranceInput.text),
            maxLines: parseInt(maxLinesInput.text),
            lineSpacing: parseInt(lineSpacingInput.text),
            alignment: alignDropdown.selection.index,
            xPosition: parseInt(xPosInput.text),
            yPosition: parseInt(yPosInput.text),
            animationType: animTypeDropdown.selection.index,
            animationSpeed: parseFloat(animSpeedInput.text) / 100,
            frameRate: parseFloat(frameRateInput.text)
        };
    } else {
        return null;
    }
}

// RGB renk stringini ayrıştırma
function parseColor(colorStr) {
    var parts = colorStr.split(",");
    if (parts.length != 3) {
        return [255, 255, 255]; // Varsayılan renk (beyaz)
    }
    
    // Global trimString fonksiyonunu kullan
    return [
        parseInt(trimString(parts[0])),
        parseInt(trimString(parts[1])),
        parseInt(trimString(parts[2]))
    ];
}

// Cümleleri birleştirme (Çift sınırlı versiyon)
function combineShortSentences(sentences, minChars, maxChars) {
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

        var trimmedOriginalSentenceText = trimString(sentence.text);
        
        if (currentSentence === null) {
            currentSentence = {
                text: sentence.text,
                start: sentence.start,
                end: sentence.end,
                length: trimmedOriginalSentenceText.length
            };
        } else {
            var timeDiff = (sentence.start !== undefined && currentSentence.end !== undefined) 
                ? Math.abs(currentSentence.end - sentence.start) 
                : 1.0;
                
            var potentialCombinedText = currentSentence.text + " " + sentence.text;
            var potentialCombinedLength = trimString(potentialCombinedText).length;
            
            // Birleştirme koşulları:
            var shouldCombine = false;
            if (potentialCombinedLength <= maxChars) { // Temel koşul: maksimumu aşmamalı
                if (currentSentence.length < minChars) {
                    shouldCombine = true; // Mevcut cümle çok kısa ve birleştirme güvenli
                } else if (timeDiff < 0.5) {
                    // Mevcut cümle çok kısa değil, ama sonraki yakın ve birleştirme güvenli
                    shouldCombine = true; 
                }
            }
            
            if (shouldCombine) {
                currentSentence.text = potentialCombinedText;
                currentSentence.end = sentence.end;
                currentSentence.length = potentialCombinedLength;
            } else {
                currentSentence.text = trimString(currentSentence.text);
                if (currentSentence.text.length > 0) {
                    result.push(currentSentence);
                }
                currentSentence = {
                    text: sentence.text,
                    start: sentence.start,
                    end: sentence.end,
                    length: trimmedOriginalSentenceText.length
                };
            }
        }
    }
    
    if (currentSentence !== null) {
        currentSentence.text = trimString(currentSentence.text);
        if (currentSentence.text.length > 0) {
            result.push(currentSentence);
        }
    }
    
    return result;
}

// Optik olarak dengeli satırlar için gelişmiş algoritma
function balancedWrapTextToLines(text, maxCharsPerLine, maxLines, minChars, maxCharTolerancePercent) {
    if (!text || !maxCharsPerLine || !maxLines) return text;
    
    // Güvenlik: Parametrelerin sayı olduğundan emin ol
    maxCharsPerLine = parseInt(maxCharsPerLine) || 50;
    maxLines = parseInt(maxLines) || 10;
    minChars = parseInt(minChars) || 30;
    maxCharTolerancePercent = parseInt(maxCharTolerancePercent) || 10;
    
    var absoluteTolerance = Math.floor(maxCharsPerLine * (maxCharTolerancePercent / 100));
    var maxLineLengthWithTolerance = maxCharsPerLine + absoluteTolerance;
    
    // Metni kelimelere ayır
    var rawWords = text.split(/\s+/);
    var words = [];
    for (var wi = 0; wi < rawWords.length; wi++) {
        if (rawWords[wi] && rawWords[wi].length > 0) {
            words.push(rawWords[wi]);
        }
    }
    
    if (!words || words.length === 0) return text;
    
    // Basitleştirilmiş satır kırma algoritması - Daha hafif
    var lines = simplifiedLineBreaking(words, maxCharsPerLine, maxLineLengthWithTolerance);
    
    // Maksimum satır sayısını kontrol et
    if (lines.length > maxLines) {
        var keptLines = lines.slice(0, maxLines - 1);
        var remainingWords = [];
        for (var i = maxLines - 1; i < lines.length; i++) {
            var lineWords = lines[i].split(/\s+/);
            for (var j = 0; j < lineWords.length; j++) {
                if (lineWords[j].length > 0) {
                    remainingWords.push(lineWords[j]);
                }
            }
        }
        lines = keptLines;
        if (remainingWords.length > 0) {
            lines.push(remainingWords.join(" "));
        }
    }
    
    // Çok kısa satırları birleştir (minChars'dan daha kısa olanlar)
    if (lines.length >= 2) {
        var balancedLines = [];
        var k = 0;
        while (k < lines.length) {
            var currentL = lines[k];
            
            if (k < lines.length - 1 && currentL.length < minChars) {
                var nextL = lines[k+1];
                var combinedLine = currentL + " " + nextL;
                
                if (combinedLine.length <= maxLineLengthWithTolerance) {
                    balancedLines.push(combinedLine);
                    k += 2;
            continue;
                }
            }
            
            balancedLines.push(currentL);
            k++;
        }
        
        // Satır uzunluklarını basit algoritma ile dengele
        lines = simpleBalanceLines(balancedLines, maxCharsPerLine, maxLineLengthWithTolerance, minChars);
    }
    
    return lines.join("\n");
}

// Basitleştirilmiş ve hafif satır kırma algoritması
function simplifiedLineBreaking(words, targetMaxChars, absoluteMaxChars) {
    var lines = [];
    var currentLine = "";
    
    for (var i = 0; i < words.length; i++) {
        var word = words[i];
        var testLine = currentLine + (currentLine.length > 0 ? " " : "") + word;
        
        if (testLine.length <= targetMaxChars) {
            // Kelime hedef maximum içinde sığıyor
            currentLine = testLine;
        } else if (testLine.length <= absoluteMaxChars) {
            // Kelime hedefi aşıyor ama tolerans içinde kalıyor
            // Mevcut satırda yeterince kelime varsa yeni satıra geç
            if (currentLine.length > 0 && currentLine.length >= targetMaxChars * 0.7) {
                lines.push(currentLine);
                currentLine = word;
            } else {
                // Aksi halde bu kelimeyi de ekle ve satırı bitir
                currentLine = testLine;
                lines.push(currentLine);
                currentLine = "";
            }
        } else {
            // Kelime tolerans sınırını da aşıyor
            if (currentLine.length > 0) {
                lines.push(currentLine);
            }
            
            // Çok uzun tek kelimeyi parçalara böl
            if (word.length > absoluteMaxChars) {
                var chunks = [];
                var start = 0;
                while (start < word.length) {
                    var end = Math.min(start + absoluteMaxChars, word.length);
                    chunks.push(word.substring(start, end));
                    start = end;
                }
                
                for (var c = 0; c < chunks.length; c++) {
                    lines.push(chunks[c]);
                }
                currentLine = "";
            } else {
                currentLine = word;
            }
        }
    }
    
    // Son satırı ekle
    if (currentLine.length > 0) {
        lines.push(currentLine);
    }
    
    return lines;
}

// Basitleştirilmiş satır dengeleme - Yoğun işlemleri azaltır
function simpleBalanceLines(lines, targetMaxChars, absoluteMaxChars, minChars) {
    if (!lines || lines.length < 2) return lines;
    
    // Ortalama satır uzunluğunu hesapla
    var totalLength = 0;
    for (var i = 0; i < lines.length; i++) {
        totalLength += lines[i].length || 0;
    }
    var avgLength = totalLength / lines.length;
    
    // Dengelemeyi sadece 3 tur yap - performans için önemli
    var maxIterations = Math.min(lines.length, 3);
    
    for (var iteration = 0; iteration < maxIterations; iteration++) {
        var anyChange = false;
        
        for (var i = 0; i < lines.length - 1; i++) {
            var line1 = lines[i] || "";
            var line2 = lines[i + 1] || "";
            
            // Satır uzunluk farkı büyükse dengelemeyi dene
            var lengthDiff = Math.abs(line1.length - line2.length);
            if (lengthDiff > 10) {
                var longLine, shortLine, longIdx, shortIdx;
                
                if (line1.length > line2.length) {
                    longLine = line1;
                    shortLine = line2;
                    longIdx = i;
                    shortIdx = i + 1;
                } else {
                    longLine = line2;
                    shortLine = line1;
                    longIdx = i + 1;
                    shortIdx = i;
                }
                
                // Uzun satırın kelimelerini al
                var longWords = longLine.split(/\s+/);
                if (longWords.length > 1) {
                    var wordToMove, newLongLine, newShortLine;
                    
                    if (longIdx < shortIdx) {
                        // Son kelimeyi taşı
                        wordToMove = longWords[longWords.length - 1];
                        newLongLine = longLine.substring(0, longLine.length - wordToMove.length - 1); // 1 boşluk için
                        newShortLine = wordToMove + " " + shortLine;
                    } else {
                        // İlk kelimeyi taşı
                        wordToMove = longWords[0];
                        newLongLine = longLine.substring(wordToMove.length + 1); // 1 boşluk için
                        newShortLine = shortLine + " " + wordToMove;
                    }
                    
                    // Yeni satır uzunluklarını kontrol et
                    if (newLongLine.length >= minChars && 
                        newShortLine.length <= absoluteMaxChars &&
                        Math.abs(newLongLine.length - newShortLine.length) < lengthDiff) {
                        
                        lines[longIdx] = newLongLine;
                        lines[shortIdx] = newShortLine;
                        anyChange = true;
                    }
                }
            }
        }
        
        // Eğer hiç değişiklik yapılmadıysa sonraki iterasyonlara gerek yok
        if (!anyChange) break;
    }
    
    return lines;
}

// Belirli bir aralıktaki kelimelerin toplam uzunluğunu hesapla (boşluklar dahil)
function getWordsLength(words, start, end) {
    var length = 0;
    for (var i = start; i <= end; i++) {
        if (words[i]) {
            length += words[i].length || 0;
        }
    }
    
    // Kelimeler arası boşluklar
    if (end > start) {
        length += (end - start);
    }
    return length;
}

// Sayfa bazlı metin gösterimi yaratma
function createPageBasedTextDisplay(comp, sentences, settings) {
    // Null veya boş sentences array kontrolü
    if (!sentences || sentences.length === 0) {
        logError("İşlenecek cümle bulunamadı!");
        return [];
    }
    
    // Debug bilgilerini başlat
    logDebug("Cümle sayısı: " + sentences.length);
    
    // Tüm sayfaları oluştur
    var pages = [];
    var remainingSentences = sentences.slice(0); // Kalan cümlelerin kopyası
    var pageIndex = 0;
    
    // Tüm cümleler işlenene kadar devam et
    while (remainingSentences.length > 0) {
        var pageSentences = []; // Bu sayfada gösterilecek cümleler
        var pageText = ""; // Bu sayfadaki metin
        var lineCount = 0;
        
        logDebug("--- SAYFA " + (pageIndex + 1) + " oluşturuluyor... (Kalan cümle: " + remainingSentences.length + ") ---");
        
        // Sayfaya sırasıyla cümle ekle ve kontrol et
        var i = 0;
        
        // En az bir cümle ekle (çok uzun olsa bile)
        if (remainingSentences.length > 0) {
            pageSentences.push(remainingSentences[0]);
            
            // İlk cümlenin metnini hazırla ve satır sayısını kontrol et
            pageText = remainingSentences[0].text || "";
            var wrappedText = balancedWrapTextToLines(pageText, settings.maxChars, settings.maxLines, settings.minChars, settings.maxCharTolerance);
            lineCount = wrappedText.split("\n").length;
            
            logDebug("  Cümle 1 eklendi, satır sayısı: " + lineCount + " (limit: " + settings.maxLines + ")");
            i = 1;
        }
        
        // Sayfa dolana kadar sonraki cümleleri test et ve ekle
        while (i < remainingSentences.length) {
            // Test için yeni cümleyi ekle
            var testSentences = pageSentences.slice(0);
            testSentences.push(remainingSentences[i]);
            
            // Test metni oluştur
            var testText = "";
            for (var j = 0; j < testSentences.length; j++) {
                testText += testSentences[j].text || "";
                if (j < testSentences.length - 1) {
                    testText += " ";
                }
            }
            
            // Test metnini ham satırlara böl ve sayısını kontrol et (overflow tespiti)
            var absoluteTolerance = Math.floor(settings.maxChars * (settings.maxCharTolerance / 100));
            var absoluteMaxChars = settings.maxChars + absoluteTolerance;
            var testWords = testText.split(/\s+/);
            var rawLines = simplifiedLineBreaking(testWords, settings.maxChars, absoluteMaxChars);
            var rawLineCount = rawLines.length;

            logDebug("  Cümle " + (i + 1) + " test: raw satır sayısı = " + rawLineCount + " (limit: " + settings.maxLines + ")");

            // Eğer gerçek satır sayısı limiti aşmıyorsa, cümleyi sayfaya ekle
            if (rawLineCount <= settings.maxLines) {
                pageSentences.push(remainingSentences[i]);
                pageText = testText;
                lineCount = rawLineCount;
                i++;
            } else {
                // Limit aşıldı, bir sonraki cümleyi ekleme
                break;
            }
        }
        
        // Sayfaya eklenen cümleleri işlenmiş olarak işaretle
        remainingSentences.splice(0, pageSentences.length);
        
        logDebug("  SAYFA " + (pageIndex + 1) + " için " + pageSentences.length + " cümle seçildi (" + lineCount + " satır)");
        
        // Sayfa boşsa, ilerlemek için en az bir cümle ekle ve devam et
        if (pageSentences.length === 0) {
            logError("Sayfaya hiç cümle eklenemedi! En az birini zorunlu ekliyorum.");
            if (remainingSentences.length > 0) {
                pageSentences.push(remainingSentences[0]);
                remainingSentences.splice(0, 1);
            } else {
                break; // Eklenecek cümle kalmadı
            }
        }
        
        try {
            // Sayfa için katmanları oluştur
            var pageStartTime = pageSentences[0].start || 0;
            var pageEndTime;
            
            if (remainingSentences.length > 0) {
                // Sonraki sayfanın başlangıcı
                pageEndTime = remainingSentences[0].start || (pageStartTime + 5);
            } else {
                // Son sayfanın sonu
                var lastSentence = pageSentences[pageSentences.length - 1];
                pageEndTime = (lastSentence && lastSentence.end) ? (lastSentence.end + 2) : (pageStartTime + 5);
            }
        
            // Metni satırlara böl
            var finalWrappedText = balancedWrapTextToLines(pageText, settings.maxChars, settings.maxLines, settings.minChars, settings.maxCharTolerance);
            var totalCharsInFinalText = finalWrappedText.length; // GERÇEK UZUNLUK
            var indexMap = mapIndices(pageText, finalWrappedText); // İndeks haritasını oluştur
            var indexMapString = "[" + indexMap.join(",") + "]"; // İfade için stringe çevir
            
            try {
                // ----- İnaktif Metin Katmanı (Gri Arka Plan) -----
                var inactiveLayer = comp.layers.addText("");
                inactiveLayer.name = "Sayfa " + (pageIndex + 1) + " - İnaktif";
                inactiveLayer.startTime = pageStartTime;
                inactiveLayer.outPoint = pageEndTime;
                
                var inactiveTextProp = inactiveLayer.property("ADBE Text Properties").property("ADBE Text Document");
                var inactiveTextDoc = inactiveTextProp.value;
                
                // Metin içeriğini ayarla
                inactiveTextDoc.text = finalWrappedText;
                
                // Font özelliklerini ayarla  
                inactiveTextDoc.fontSize = settings.fontSize;
                inactiveTextDoc.fillColor = [settings.inactiveFontColor[0]/255, settings.inactiveFontColor[1]/255, settings.inactiveFontColor[2]/255];
                
                inactiveTextProp.setValue(inactiveTextDoc);
                
                // İnaktif pozisyonu
                var inactivePosition = inactiveLayer.property("ADBE Transform Group").property("ADBE Position");
                var calculatedX, calculatedY;
                calculatedY = comp.height * (settings.yPosition / 100);
                
                if (settings.alignment === 0) { // Ortala 
                    calculatedX = comp.width / 2;
                } else if (settings.alignment === 1) { // Sol
                    calculatedX = comp.width * (settings.xPosition / 100);
                } else { // Sağ
                    calculatedX = comp.width * (1 - settings.xPosition / 100);
                }
                
                inactivePosition.setValue([calculatedX, calculatedY]);
            } catch (textError) {
                logError("İnaktif metin katmanı oluşturulurken hata: " + textError.toString());
                throw textError; // Hatayı yeniden fırlat
            }

            try {
                // ----- Aktif Metin Katmanı (Beyaz Vurgulu) -----
                var activeLayer = comp.layers.addText("");
                activeLayer.name = "Sayfa " + (pageIndex + 1) + " - Aktif";
                activeLayer.startTime = pageStartTime;
                activeLayer.outPoint = pageEndTime;
                
                var activeTextProp = activeLayer.property("ADBE Text Properties").property("ADBE Text Document");
                var activeTextDoc = activeTextProp.value;
                
                // Metin içeriğini ayarla
                activeTextDoc.text = finalWrappedText;
                
                // Font özelliklerini ayarla  
                activeTextDoc.fontSize = settings.fontSize;
                activeTextDoc.fillColor = [settings.activeFontColor[0]/255, settings.activeFontColor[1]/255, settings.activeFontColor[2]/255];
                
                activeTextProp.setValue(activeTextDoc);
                
                // Aktif pozisyonu (inaktif ile aynı)
                var activePosition = activeLayer.property("ADBE Transform Group").property("ADBE Position");
                activePosition.setValue([calculatedX, calculatedY]);
            } catch (textError) {
                logError("Aktif metin katmanı oluşturulurken hata: " + textError.toString());
                throw textError; // Hatayı yeniden fırlat
            }
        
            // Animatör için cümle verilerini hazırla - Kodu düzeltildi
            var sentencesDataForExpression = [];
            var currentCharIndex = 0; // Bu hala SARILMAMIŞ pageText'e göre

            for (var n = 0; n < pageSentences.length; n++) {
                var sentenceObj = pageSentences[n];
                var sText = sentenceObj.text || "";
                var sStart = sentenceObj.start || 0;
                var sEnd = sentenceObj.end || (sStart + 1);
                
                // Bitiş başlangıçtan sonra olmalı
                if (sEnd <= sStart) sEnd = sStart + 0.001;

                sentencesDataForExpression.push(
                    "{s:" + (sStart - pageStartTime) + 
                    ",e:" + (sEnd - pageStartTime) + 
                    ",cs:" + currentCharIndex + // Sarılmamış başlangıç indeksi
                    ",textLen:" + sText.length + "}" // Sarılmamış uzunluk
                );

                currentCharIndex += sText.length;

                // Cümleler arası boşluğu ekle
                if (n < pageSentences.length - 1) {
                    currentCharIndex++;
                }
            }
            
            // Animasyon ekle
            if (settings.animationType === 0 || settings.animationType === 1) {
                var textAnimator;
                var rangeSelector;
                
                try {
                    // Animatör ekle
                    var animatorsGroup = activeLayer.property("ADBE Text Properties").property("ADBE Text Animators");
                    textAnimator = animatorsGroup.addProperty("ADBE Text Animator");

                    // Opaklık ekle
                    var animatorProperties = textAnimator.property("ADBE Text Animator Properties");
                    var opacityProperty = animatorProperties.addProperty("ADBE Text Opacity");
                    opacityProperty.setValue(0); // Animatörden etkilenen karakterler %0 opaklıkta
                    
                    // Range selector ekle
                    var selectorsGroup = textAnimator.property("ADBE Text Selectors");
                    rangeSelector = selectorsGroup.addProperty("ADBE Text Selector");
                    
                    // Birimler olarak karakter indeksini kullan
            var unitsProp = null;
                    var advancedRangeSelectorProps = rangeSelector.property("ADBE Text Range Advanced");

            if (advancedRangeSelectorProps) {
                unitsProp = advancedRangeSelectorProps.property("ADBE Text Range Units");
                    }

                    if (!unitsProp) {
                unitsProp = rangeSelector.property("Units"); 
                    }
                    
                    if (unitsProp) {
                        unitsProp.setValue(2); // 2: İndeks (karakter indeksi)
                    }
                    
                    // Range Start/End
                    var rangeStartProp = rangeSelector.property("ADBE Text Index Start");
                    var rangeEndProp = rangeSelector.property("ADBE Text Index End");
            
                    if (rangeStartProp && rangeEndProp) {
                        // İfade oluştur (Basitleştirilmiş - 1sn Erken Bitiş)
                        var expressionText = "" +
                        "var layerTime = time - thisLayer.inPoint;\n" +
                        "var frameRate = " + settings.frameRate + ";\n" +
                        "if (frameRate <= 0) frameRate = 1 / thisComp.frameDuration;\n" +
                        "var currentFrame = Math.round(layerTime * frameRate);\n" +
                        "var sentencesData = [" + sentencesDataForExpression.join(",") + "];\n" +
                        "var animationType = " + settings.animationType + ";\n" +
                        "var indexMap = " + indexMapString + ";\n" + // Index haritasını ifadeye ekle
                        "var charsToReveal = 0;\n" +
                        "var numSentences = sentencesData.length;\n" +
                        // "var onePointFiveSecondsInFrames = Math.round(1.5 * frameRate); \n" + // Erken bitirme İPTAL
                        
                        "if (numSentences > 0) {\n" +
                        "    var firstStartFrame = Math.round(sentencesData[0].s * frameRate);\n" +
                        
                        "    if (currentFrame < firstStartFrame) {\n" +
                        "        // İlk cümleden önce: charsToReveal = 0 (varsayılan)\n" +
                        "    } else {\n" +
                        "        // Cümleleri dönerek aktif olanı veya son durumu bul\n" +
                        "        var foundState = false;\n" + // Aktif veya boşluk durumu bulundu mu?
                        "        for (var i = 0; i < numSentences; i++) {\n" +
                        "            var s = sentencesData[i];\n" +
                        "            var startFrame = Math.round(s.s * frameRate);\n" +
                        "            var originalEndFrame = Math.round(s.e * frameRate);\n" +
                        "            var endFrame = Math.max(startFrame + 1, originalEndFrame);\n" +
                        "            var sentenceCharStartIndex = s.cs;\n" +
                        "            var sentenceCharLength = s.textLen;\n" +
                        "            var sentenceCharEndIndex = sentenceCharStartIndex + sentenceCharLength; // Sarılmamış metindeki bitiş indeksi\n" +

                        "            // 1. Aktif Cümle Aralığı\n" +
                        "            if (currentFrame >= startFrame && currentFrame <= endFrame && sentenceCharLength > 0) {\n" +
                        "                if (animationType === 0) { // Harf Harf\n" +
                        "                    // Hedef indeksi SARILMAMIŞ metne göre hesapla\n" +
                        "                    var targetUnwrappedIndex = linear(currentFrame, startFrame, endFrame, sentenceCharStartIndex, sentenceCharEndIndex);\n" +
                        "                    targetUnwrappedIndex = Math.round(targetUnwrappedIndex);\n" +
                        "                    // Haritada geçerli bir aralığa kelepçele\n" +
                        "                    targetUnwrappedIndex = Math.max(0, Math.min(indexMap.length - 1, targetUnwrappedIndex));\n" +
                        "                    // SARILMIŞ metindeki karşılık gelen indeksi haritadan bul\n" +
                        "                    if (indexMap.length > targetUnwrappedIndex) {\n" +
                        "                       charsToReveal = indexMap[targetUnwrappedIndex];\n" +
                        "                    } else { charsToReveal = thisLayer.text.sourceText.length; } // Fallback\n" +
                        "                } else { // Anında\n" +
                        "                    // Sarılmamış bitiş indeksini haritada bul\n" +
                        "                    var endUnwrappedIndex = Math.min(indexMap.length - 1, sentenceCharEndIndex);\n" +
                        "                    if (indexMap.length > endUnwrappedIndex) {\n" +
                        "                       charsToReveal = indexMap[endUnwrappedIndex];\n" +
                        "                    } else { charsToReveal = thisLayer.text.sourceText.length; } // Fallback\n" +
                        "                }\n" +
                        "                foundState = true;\n" +
                        "                break; \n" +
                        "            }\n" +
                        
                        "            // 2. Cümle Başlangıcından Önce (Boşluk)\n" +
                        "            else if (currentFrame < startFrame) {\n" +
                        "                if (i > 0) { \n" +
                        "                    var prevSentence = sentencesData[i-1];\n" +
                        "                    // Önceki cümlenin sarılmamış bitiş indeksini haritada bul\n" +
                        "                    var prevEndUnwrapped = Math.min(indexMap.length - 1, prevSentence.cs + prevSentence.textLen);\n" +
                        "                    if (indexMap.length > prevEndUnwrapped) {\n" +
                        "                       charsToReveal = indexMap[prevEndUnwrapped];\n" +
                        "                    } else { charsToReveal = thisLayer.text.sourceText.length; } // Fallback\n" +
                        "                    foundState = true;\n" +
                        "                    break; \n" +
                        "                } \n" +
                        "            }\n" +
                        
                        "            // 3. Cümle Bitişinden Sonra \n" +
                        "            else if (currentFrame > endFrame) {\n" +
                        "                 // Bu cümlenin sarılmamış bitiş indeksini haritada bul\n" +
                        "                 var thisEndUnwrapped = Math.min(indexMap.length - 1, sentenceCharEndIndex);\n" +
                        "                 if (indexMap.length > thisEndUnwrapped) {\n" +
                        "                    charsToReveal = indexMap[thisEndUnwrapped];\n" +
                        "                 } else { charsToReveal = thisLayer.text.sourceText.length; } // Fallback\n" +
                        "                 // Döngüye devam... \n" +
                        "            }\n" +
                        "        }\n" +
                        "        // Döngü bittikten sonra 'foundState' hala false ise, bu son cümlenin bitişinden sonrasıdır.\n" +
                        "        // charsToReveal zaten son döngüdeki 'else if (currentFrame > endFrame)' ile doğru ayarlanmış olmalı.\n" +
                        "    }\n" +
                        "} \n" +

                        "charsToReveal;"; // İfade sonucu

                        rangeStartProp.expression = expressionText;
                        rangeEndProp.setValue(totalCharsInFinalText); // Toplam karakter sayısını GÜNCELLE
                    }
                } catch (animError) {
                    logError("Animasyon eklenirken: " + animError.toString());
                    // Animasyon hatası kritik değil, devam et
                }
            }
        
            // Katmanları sayfalar listesine ekle
        pages.push(inactiveLayer); 
        pages.push(activeLayer); 
            
            // Sonraki sayfaya geç
            pageIndex++;
            
            logDebug("  Sayfa " + pageIndex + " tamamlandı. Kalan cümle sayısı: " + remainingSentences.length + "/" + sentences.length);
            
        } catch (e) {
            logError("KRİTİK HATA: " + e.toString());
            pageIndex++;
            
            // İlerleme sağlamak için kalan cümlelerden birini sil
            if (remainingSentences.length > 0) {
                remainingSentences.splice(0, 1);
            }
        }
    }
        
    // Özet bilgileri
    if (pages.length === 0) {
        showError("Sayfa Oluşturma Hatası", "Hiç sayfa oluşturulamadı!\n\nTam hata raporu panoya kopyalanabilir.");
    } else if (pages.length === 2) {
        showError("Olası Sayfa Oluşturma Sorunu", "Sadece 1 sayfa oluşturuldu, hata olabilir!\n\nTam hata raporu panoya kopyalanabilir.");
    } else {
        alert(pages.length / 2 + " sayfa başarıyla oluşturuldu.");
    }
    
    return pages;
}

// Ana işlev
function createTextDisplayEffect() {
    try {
    // Kullanıcı ayarlarını al
    var settings = showSettingsDialog();
    if (settings === null) {
        return; // Kullanıcı iptal etti
    }

    // SRT dosyasını seç
    var srtFile = File.openDialog("SRT dosyasını seçin", "SRT:*.srt");
    if (srtFile === null) {
        alert("Dosya seçilmedi.");
        return;
    }

        // Dosyayı aç ve içeriği oku
        srtFile.open("r");
        var srtContent = srtFile.read();
        srtFile.close();
        
        // SRT içeriğini ayrıştır
        var sentences;
        try {
            // Yeni parseSRT fonksiyonu kullanarak SRT'yi ayrıştır
            sentences = parseSRT(srtContent);
            
            if (!sentences || !sentences.length) {
                showError("SRT Ayrıştırma Hatası", "Cümle bulunamadı veya SRT biçimi hatalı.");
                return;
            }
            
            logDebug("SRT başarıyla ayrıştırıldı. " + sentences.length + " cümle bulundu.");
            
            // Debug bilgisi: İlk birkaç cümlenin içeriğini göster
            for (var i = 0; i < Math.min(sentences.length, 3); i++) {
                logDebug("Cümle #" + (i+1) + ": '" + sentences[i].text.substring(0, 50) + "...' - Süre: " + sentences[i].start + " -> " + sentences[i].end);
            }
            
        } catch (error) {
            showError("SRT Ayrıştırma Hatası", "SRT dosyası ayrıştırılırken hata oluştu: " + error.message);
            return;
        }
        
        // Cümle sayısı kontrolü
        if (sentences.length <= 1) {
            showError("Yetersiz Cümle", "SRT dosyasında sadece " + sentences.length + " cümle bulundu. Daha fazla cümle içeren bir dosya seçin.");
            return;
        }
        
        // Kısa cümleleri birleştir
        if (settings.minChars > 0 || settings.maxChars > 0) {
            var originalCount = sentences.length;
            sentences = combineShortSentences(sentences, settings.minChars, settings.maxChars);
            logDebug("Cümleler " + settings.minChars + "-" + settings.maxChars + " karakter aralığına göre birleştirildi. Cümle sayısı: " + originalCount + " -> " + sentences.length);
            
            // Debug bilgisi: Birleştirme sonrası ilk birkaç cümle
            for (var i = 0; i < Math.min(sentences.length, 3); i++) {
                logDebug("Birleştirme sonrası #" + (i+1) + ": '" + sentences[i].text.substring(0, 50) + "...' - Süre: " + sentences[i].start + " -> " + sentences[i].end);
            }
            
            // Eğer tüm cümleler birleştirilmişse uyarı ver
            if (sentences.length <= 1) {
                var userContinue = confirm("Tüm cümleler birleştirildi ve tek bir cümle oluştu. Bu, tek sayfa oluşmasına neden olacak. Devam etmek istiyor musunuz?");
                if (!userContinue) {
                    return;
                }
            }
        }
        
        // Aktif kompozisyonu al
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) {
            showError("Kompozisyon Hatası", "Lütfen bir kompozisyon açın.");
            return;
        }
        
        // Sayfa bazlı metin gösterimi oluştur
        logDebug("Sayfalandırma başlatılıyor - Toplam cümle sayısı: " + sentences.length);
        var textLayers = createPageBasedTextDisplay(comp, sentences, settings);
        
    } catch (mainError) {
        showError("Script Hatası", "Script çalışırken bir hata oluştu:\n\n" + mainError.toString() + "\n\nTam hata raporu panoya kopyalanabilir.");
    }
}

// Scripti çalıştır
createTextDisplayEffect();