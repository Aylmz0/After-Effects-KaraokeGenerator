from faster_whisper import WhisperModel
import json
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import time

class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Faster Whisper Arayüzü")
        self.root.geometry("650x700")
        self.root.resizable(True, True)
        
        # Değişkenler
        self.audio_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.srt_path = tk.StringVar() # For optional SRT file input
        self.model_size = tk.StringVar(value="medium")  # Türkçe için medium daha iyi
        
        # Gelişmiş ayarlar için değişkenler
        self.language = tk.StringVar(value="tr")  # Türkçe varsayılan
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.IntVar(value=5)
        self.vad_filter = tk.BooleanVar(value=True)
        self.vad_threshold = tk.DoubleVar(value=0.5)
        self.temperature = tk.DoubleVar(value=0.0)
        self.initial_prompt = tk.StringVar(value="")
        self.word_timestamps = tk.BooleanVar(value=True)
        
        # Notebook oluştur (sekmeler için)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Ana ayarlar sekmesi
        main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(main_frame, text="Ana Ayarlar")
        
        # Gelişmiş ayarlar sekmesi
        advanced_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(advanced_frame, text="Gelişmiş Ayarlar")
        
        # Yardım sekmesi
        help_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(help_frame, text="Yardım ve Bilgi")
        
        # Düzeltme Aracı sekmesi
        self.correction_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.correction_frame, text="Düzeltme Aracı")
        
        # Ana ayarlar sekmesini doldur
        ttk.Label(main_frame, text="Ses Dosyası:").grid(column=0, row=0, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.audio_path).grid(column=0, row=1, sticky="ew")
        ttk.Button(main_frame, text="Dosya Seç", command=self.select_audio).grid(column=1, row=1, padx=5)
        
        ttk.Label(main_frame, text="Çıktı Dosyası:").grid(column=0, row=2, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.output_path).grid(column=0, row=3, sticky="ew")
        ttk.Button(main_frame, text="Konum Seç", command=self.select_output).grid(column=1, row=3, padx=5)
        
        # SRT Dosyası Seçimi (İsteğe Bağlı)
        ttk.Label(main_frame, text="SRT Dosyası (İsteğe Bağlı - Metin İyileştirme İçin):").grid(column=0, row=4, sticky="w", pady=5)
        ttk.Entry(main_frame, width=50, textvariable=self.srt_path).grid(column=0, row=5, sticky="ew")
        ttk.Button(main_frame, text="SRT Seç", command=self.select_srt).grid(column=1, row=5, padx=5)
        
        ttk.Label(main_frame, text="Model Büyüklüğü:").grid(column=0, row=6, sticky="w", pady=5)
        model_combo = ttk.Combobox(main_frame, textvariable=self.model_size)
        model_combo['values'] = ("tiny", "base", "small", "medium", "large", "large-v2")
        model_combo.grid(column=0, row=7, sticky="ew")
        model_combo.current(3)  # Medium varsayılan (Türkçe için daha iyi)
        ttk.Label(main_frame, text="(Türkçe için medium veya large önerilir)").grid(column=0, row=8, sticky="w", pady=(0,5))
        
        ttk.Label(main_frame, text="Dil:").grid(column=0, row=9, sticky="w", pady=5)
        language_combo = ttk.Combobox(main_frame, textvariable=self.language)
        language_combo['values'] = ("tr", "auto", "en", "de", "fr", "es", "it")
        language_combo.grid(column=0, row=10, sticky="ew")
        language_combo.current(0)  # Türkçe varsayılan
        
        ttk.Separator(main_frame, orient="horizontal").grid(column=0, row=11, columnspan=2, sticky="ew", pady=15)
        
        # Tam metin ipucu (prompt) alanı
        ttk.Label(main_frame, text="Tam Metin (Doğruluğu Arttırır):").grid(column=0, row=12, sticky="w", pady=5)
        ttk.Label(main_frame, text="Ses kaydının tam metnini biliyorsanız, buraya yapıştırın:").grid(column=0, row=13, sticky="w", pady=(0,5))
        self.full_text_prompt = scrolledtext.ScrolledText(main_frame, width=50, height=6, wrap=tk.WORD)
        self.full_text_prompt.grid(column=0, row=14, columnspan=2, sticky="ew", pady=5)
        
        # İşlem butonu
        ttk.Button(main_frame, text="Transkripsiyon Başlat", command=self.run_transcription).grid(column=0, row=15, columnspan=2, pady=20)
        
        # Durum göstergesi
        self.status = tk.StringVar(value="Hazır")
        ttk.Label(main_frame, textvariable=self.status).grid(column=0, row=16, columnspan=2)
        
        # Gelişmiş ayarlar sekmesini doldur
        ttk.Label(advanced_frame, text="Compute Type:").grid(column=0, row=0, sticky="w", pady=5)
        compute_combo = ttk.Combobox(advanced_frame, textvariable=self.compute_type)
        compute_combo['values'] = ("int8", "int8_float16", "float16", "float32")
        compute_combo.grid(column=1, row=0, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Hesaplama tipi - int8 daha hızlı, float16/32 daha doğru)").grid(column=0, row=1, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Beam Size:").grid(column=0, row=2, sticky="w", pady=5)
        beam_spin = ttk.Spinbox(advanced_frame, from_=1, to=10, textvariable=self.beam_size)
        beam_spin.grid(column=1, row=2, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Daha yüksek değer daha doğru sonuç verir ancak yavaşlatır)").grid(column=0, row=3, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="VAD Filtresi:").grid(column=0, row=4, sticky="w", pady=5)
        ttk.Checkbutton(advanced_frame, variable=self.vad_filter).grid(column=1, row=4, sticky="w", padx=10)
        ttk.Label(advanced_frame, text="(Sessiz bölümleri filtreler, konuşma tanımayı iyileştirir)").grid(column=0, row=5, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="VAD Eşiği:").grid(column=0, row=6, sticky="w", pady=5)
        vad_scale = ttk.Scale(advanced_frame, from_=0.1, to=0.9, orient="horizontal", variable=self.vad_threshold)
        vad_scale.grid(column=1, row=6, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Daha düşük değer daha fazla sesi algılar, yüksek değer daha seçicidir)").grid(column=0, row=7, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Temperature:").grid(column=0, row=8, sticky="w", pady=5)
        temp_scale = ttk.Scale(advanced_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.temperature)
        temp_scale.grid(column=1, row=8, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(0: en olası sonuç, yüksek değer: daha yaratıcı sonuçlar)").grid(column=0, row=9, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="İlk İpucu Metni:").grid(column=0, row=10, sticky="w", pady=5)
        ttk.Entry(advanced_frame, width=40, textvariable=self.initial_prompt).grid(column=1, row=10, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Modele başlangıç ipucu, 'Bu bir Türkçe konuşma kaydıdır' gibi)").grid(column=0, row=11, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Kelime Zamanlamaları:").grid(column=0, row=12, sticky="w", pady=5)
        ttk.Checkbutton(advanced_frame, variable=self.word_timestamps).grid(column=1, row=12, sticky="w", padx=10)
        ttk.Label(advanced_frame, text="(Her kelime için ayrı zaman bilgisi, kapalıysa cümle zamanları)").grid(column=0, row=13, columnspan=2, sticky="w", pady=(0,5))
        
        # Türkçe için öneriler
        ttk.Separator(advanced_frame, orient="horizontal").grid(column=0, row=14, columnspan=2, sticky="ew", pady=15)
        ttk.Label(advanced_frame, text="Türkçe İçin Önerilen Ayarlar", font=("", 10, "bold")).grid(column=0, row=15, columnspan=2, sticky="w", pady=5)
        ttk.Label(advanced_frame, text="- Medium veya Large model kullanın").grid(column=0, row=16, columnspan=2, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- VAD filtresi açık olmalı").grid(column=0, row=17, columnspan=2, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- Beam Size 5 ideal").grid(column=0, row=18, columnspan=2, sticky="w", pady=2)
        
        # Varsayılan ayarları yükle butonu
        ttk.Button(advanced_frame, text="Türkçe İçin Varsayılanları Yükle", command=self.load_turkish_defaults).grid(column=0, row=19, columnspan=2, pady=20)
        
        # Yardım sekmesi içeriği
        help_content = """
WHISPER MODELİ AYARLARI HAKKINDA BİLGİLENDİRME

1. MODEL BÜYÜKLÜĞÜ
   - tiny: En küçük model, hızlı ama daha az doğru
   - base: Küçük, dengeli model
   - small: Orta büyüklükte, dengeli
   - medium: Türkçe için iyi, doğruluk/hız dengeli
   - large/large-v2: En büyük, en doğru ama yavaş model

2. COMPUTE TYPE
   - int8: En hızlı, hafıza dostu ama daha az hassas
   - float16/32: Daha doğru ama daha fazla hafıza kullanır ve yavaştır

3. BEAM SIZE
   - Değer arttıkça, model farklı olasılıkları daha fazla değerlendirir
   - Türkçe için 5 genelde iyi sonuç verir
   - Yüksek değerler işlemi yavaşlatır

4. VAD FİLTRESİ (Voice Activity Detection)
   - Ses kaydında sadece konuşma olan kısımları işler
   - Sessiz bölümleri atlar, gürültüyü azaltır
   - Türkçe için açık olması önerilir

5. TEMPERATURE
   - 0.0: En olası sonuçları seçer (en doğru)
   - Yükseldikçe: Modelin çeşitliliği artar, yaratıcılığı artar
   - Gerçek konuşma kayıtları için düşük tutun

6. TAM METİN KULLANIMI
   - Ses kaydının tam metnini biliyorsanız, yazın
   - Model bu metni referans alarak kelimeleri doğru eşleştirir
   - Zamanlama doğruluğunu önemli ölçüde artırır

7. KELİME ZAMANLAMALARI
   - Açık: Her kelime için başlangıç/bitiş zamanı
   - Kapalı: Cümle/segment başına tek zaman

8. İLK İPUCU METNİ
   - Modele başlangıç için verilen metin ipucu
   - Örnek: "Bu bir Türkçe ders anlatımıdır"
   - İçerik türünü belirtmek doğruluğu artırır

BU PROGRAM HAKKINDA
Bu program, Faster Whisper modelini kullanarak ses dosyalarını yazıya 
dönüştürür ve kelimelerin zaman damgalarını çıkarır. Özellikle
Türkçe ses kayıtları için optimize edilmiştir.
        """
        
        help_text = scrolledtext.ScrolledText(help_frame, width=60, height=30, wrap=tk.WORD)
        help_text.pack(fill="both", expand=True, padx=5, pady=5)
        help_text.insert(tk.END, help_content)
        help_text.config(state="disabled")  # Salt okunur
        
        # Sütun ve satır ağırlıklarını ayarla
        main_frame.columnconfigure(0, weight=1)
        advanced_frame.columnconfigure(1, weight=1)
        self.correction_frame.columnconfigure(0, weight=1) # Correction frame column weight
        self.correction_frame.columnconfigure(2, weight=0) # Button column

        self._create_correction_tab_widgets() # Call method to populate the new tab
    
    def _create_correction_tab_widgets(self):
        """Düzeltme Aracı sekmesinin içeriğini oluşturur."""
        # JSON Dosyası
        ttk.Label(self.correction_frame, text="JSON Dosyası (Düzeltilecek):").grid(column=0, row=0, sticky="w", pady=(5,0), columnspan=2)
        self.correction_json_path = tk.StringVar()
        ttk.Entry(self.correction_frame, width=50, textvariable=self.correction_json_path).grid(column=0, row=1, sticky="ew", columnspan=1, padx=(0,5))
        ttk.Button(self.correction_frame, text="JSON Seç", command=self._select_correction_json).grid(column=1, row=1, padx=5, sticky="w")

        # Referans TXT Dosyası
        ttk.Label(self.correction_frame, text="Referans TXT Dosyası (Karşılaştırma için):").grid(column=0, row=2, sticky="w", pady=(10,0), columnspan=2)
        self.correction_txt_path = tk.StringVar()
        ttk.Entry(self.correction_frame, width=50, textvariable=self.correction_txt_path).grid(column=0, row=3, sticky="ew", columnspan=1, padx=(0,5))
        ttk.Button(self.correction_frame, text="TXT Seç", command=self._select_correction_txt).grid(column=1, row=3, padx=5, sticky="w")

        # Kontrol Butonları
        control_buttons_frame = ttk.Frame(self.correction_frame)
        control_buttons_frame.grid(column=0, row=4, columnspan=2, pady=10, sticky="ew")
        
        ttk.Button(control_buttons_frame, text="Dosyaları Yükle ve Görüntüle", command=self._load_files_for_correction).pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(control_buttons_frame, text="Düzeltilmiş JSON'u Kaydet", command=self._save_corrected_json).pack(side=tk.LEFT)

        # Metin Alanları Paneli
        text_areas_frame = ttk.Frame(self.correction_frame)
        text_areas_frame.grid(column=0, row=5, columnspan=2, sticky="nsew", pady=(5,0))
        text_areas_frame.columnconfigure(0, weight=1)
        text_areas_frame.columnconfigure(1, weight=1)
        text_areas_frame.rowconfigure(1, weight=1)

        ttk.Label(text_areas_frame, text="JSON Metinleri (Düzenlenebilir):").grid(column=0, row=0, sticky="w", pady=(0,2))
        self.json_texts_display = scrolledtext.ScrolledText(text_areas_frame, width=40, height=15, wrap=tk.WORD)
        self.json_texts_display.grid(column=0, row=1, sticky="nsew", padx=(0,5))
        
        ttk.Label(text_areas_frame, text="TXT İçeriği (Salt Okunur):").grid(column=1, row=0, sticky="w", pady=(0,2))
        self.txt_lines_display = scrolledtext.ScrolledText(text_areas_frame, width=40, height=15, wrap=tk.WORD, state="disabled")
        self.txt_lines_display.grid(column=1, row=1, sticky="nsew", padx=(5,0))

        self.correction_frame.rowconfigure(5, weight=1) # Metin alanlarının bulunduğu satır genişlesin
        
        self.current_correction_data = None # Yüklenen JSON verisini saklamak için

    def _load_files_for_correction(self):
        json_path = self.correction_json_path.get()
        txt_path = self.correction_txt_path.get()

        if not json_path or not txt_path:
            messagebox.showwarning("Eksik Bilgi", "Lütfen hem JSON hem de referans TXT dosyasını seçin.")
            return

        # Metin alanlarını temizle
        self.json_texts_display.config(state="normal")
        self.json_texts_display.delete("1.0", tk.END)
        self.txt_lines_display.config(state="normal")
        self.txt_lines_display.delete("1.0", tk.END)

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.current_correction_data = json.load(f)
            
            if not isinstance(self.current_correction_data, list):
                messagebox.showerror("JSON Format Hatası", "JSON dosyası beklenen formatta değil (kelime/segment listesi bekleniyor).")
                self.current_correction_data = None
                return

            for item in self.current_correction_data:
                if isinstance(item, dict) and 'text' in item:
                    self.json_texts_display.insert(tk.END, str(item.get('text', '')) + '\\n')
                else:
                    # Beklenmedik bir format varsa, kullanıcıyı uyar ve boş satır ekle
                    self.json_texts_display.insert(tk.END, '\\n')
                    print(f"Uyarı: JSON içinde beklenmedik formatta öğe: {item}")


        except Exception as e:
            messagebox.showerror("JSON Okuma Hatası", f"JSON dosyası okunurken hata oluştu: {str(e)}")
            self.current_correction_data = None
            return

        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.txt_lines_display.insert(tk.END, line)
            self.txt_lines_display.config(state="disabled") # TXT alanı salt okunur kalsın
        except Exception as e:
            messagebox.showerror("TXT Okuma Hatası", f"TXT dosyası okunurken hata oluştu: {str(e)}")
            self.txt_lines_display.config(state="disabled")


    def _save_corrected_json(self):
        if not self.current_correction_data:
            messagebox.showwarning("Veri Yok", "Önce JSON verisini yükleyin ve düzenleyin.")
            return

        edited_lines = self.json_texts_display.get("1.0", tk.END).strip().split('\\n')
        
        if len(edited_lines) != len(self.current_correction_data):
            # Kullanıcı satır eklemiş veya silmişse, bu basit güncelleme yöntemi sorun yaratabilir.
            # Şimdilik sadece uyaralım. Daha gelişmiş bir eşleştirme gerekebilir.
            if messagebox.askyesno("Satır Sayısı Uyuşmazlığı", 
                                   f"Düzenlenen metin satır sayısı ({len(edited_lines)}) ile orijinal JSON öğe sayısı ({len(self.current_correction_data)}) farklı.\\n"
                                   "Bu durum, özellikle satır sildiyseniz veya eklediyseniz, verilerin yanlış eşleşmesine neden olabilir.\\n"
                                   "Devam etmek istiyor musunuz? (İlk {min(len(edited_lines), len(self.current_correction_data))} öğe güncellenecek)"):
                pass # Kullanıcı devam etmek istiyor
            else:
                return # Kullanıcı iptal etti

        updated_count = 0
        min_len = min(len(edited_lines), len(self.current_correction_data))

        for i in range(min_len):
            if isinstance(self.current_correction_data[i], dict) and 'text' in self.current_correction_data[i]:
                self.current_correction_data[i]['text'] = edited_lines[i]
                updated_count +=1
            else:
                print(f"Uyarı: Kayıt sırasında {i}. indeksteki JSON öğesi beklenmedik formatta, atlanıyor.")


        save_path = filedialog.asksaveasfilename(
            title="Düzeltilmiş JSON Dosyasını Kaydet",
            defaultextension=".json",
            filetypes=[("JSON Dosyaları", "*.json")],
            initialfile=self.correction_json_path.get() # Orijinal dosya adını öner
        )

        if not save_path:
            return # Kullanıcı iptal etti

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.current_correction_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Başarılı", f"{updated_count} öğe güncellenerek düzeltilmiş JSON dosyası kaydedildi: {save_path}")
        except Exception as e:
            messagebox.showerror("Kayıt Hatası", f"JSON dosyası kaydedilirken hata oluştu: {str(e)}")


    def _select_correction_json(self):
        file_path = filedialog.askopenfilename(
            title="Düzeltilecek JSON Dosyasını Seç",
            filetypes=[("JSON Dosyaları", "*.json")]
        )
        if file_path:
            self.correction_json_path.set(file_path)
            # Otomatik olarak output_path'i de set etmeyi düşünebiliriz
            # self.output_path.set(file_path) 

    def _select_correction_txt(self):
        file_path = filedialog.askopenfilename(
            title="Referans TXT Dosyasını Seç",
            filetypes=[("Metin Dosyaları", "*.txt")]
        )
        if file_path:
            self.correction_txt_path.set(file_path)

    def load_turkish_defaults(self):
        """Türkçe için en iyi ayarları yükler."""
        self.model_size.set("medium")
        self.language.set("tr")
        self.compute_type.set("int8")
        self.beam_size.set(5)
        self.vad_filter.set(True)
        self.vad_threshold.set(0.5)
        self.temperature.set(0.0)
        self.initial_prompt.set("Bu bir Türkçe konuşma kaydıdır.")
        self.word_timestamps.set(True)
        messagebox.showinfo("Bilgi", "Türkçe için önerilen ayarlar yüklendi.")
    
    def select_audio(self):
        file_path = filedialog.askopenfilename(
            title="Ses Dosyası Seç",
            filetypes=[("Ses Dosyaları", "*.wav;*.mp3;*.m4a;*.ogg;*.flac")]
        )
        if file_path:
            self.audio_path.set(file_path)
            # Varsayılan olarak aynı dizinde çıktı oluştur
            filename = os.path.splitext(os.path.basename(file_path))[0]
            default_output = os.path.join(os.path.dirname(file_path), f"{filename}_zamanlar.json")
            self.output_path.set(default_output)
    
    def select_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Çıktı Dosyasını Kaydet",
            defaultextension=".json",
            filetypes=[("JSON Dosyaları", "*.json")]
        )
        if file_path:
            self.output_path.set(file_path)
    
    def select_srt(self):
        file_path = filedialog.askopenfilename(
            title="SRT Dosyası Seç",
            filetypes=[("SRT Dosyaları", "*.srt")]
        )
        if file_path:
            self.srt_path.set(file_path)        

    def parse_srt_for_text(self, srt_file_path):
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            blocks = content.strip().split('\n\n')
            all_text = []
            for block in blocks:
                lines = block.split('\n')
                if len(lines) >= 3: # Sequence, Time, Text...
                    text_lines = lines[2:]
                    all_text.append(" ".join(text_lines).strip())
            return " ".join(all_text).strip() if all_text else None
        except Exception as e:
            messagebox.showwarning("SRT Okuma Hatası", f"SRT dosyası okunurken/ayrıştırılırken hata oluştu: {str(e)}\nSRT metni ipucu olarak kullanılamayacak.")
            return None
    
    def run_transcription(self):
        # Gerekli alanları kontrol et
        if not self.audio_path.get():
            messagebox.showerror("Hata", "Lütfen bir ses dosyası seçin.")
            return
        
        if not self.output_path.get():
            messagebox.showerror("Hata", "Lütfen çıktı dosyası konumunu seçin.")
            return
        
        try:
            self.status.set("Model yükleniyor...")
            self.root.update()
            
            start_time = time.time() # Record start time
            # Modeli yükle
            model_size = self.model_size.get()
            model = WhisperModel(model_size, device="cpu", compute_type=self.compute_type.get())
            
            self.status.set("Transkripsiyon için hazırlanıyor...") # Changed status message
            self.root.update()
            
            # Gelişmiş ayarları topla
            language = None if self.language.get() == "auto" else self.language.get()
            
            # Determine the initial_prompt for Whisper
            initial_prompt_for_model = None
            prompt_source_status = "İpucu metni kullanılmıyor..." # Default status
            
            full_text_from_main_tab = self.full_text_prompt.get("1.0", tk.END).strip()
            srt_file_path_str = self.srt_path.get().strip()
            specific_initial_prompt = self.initial_prompt.get().strip() # From advanced settings

            if full_text_from_main_tab:
                initial_prompt_for_model = full_text_from_main_tab
                prompt_source_status = "Sağlanan TXT metni, yazım/noktalama düzeltmelerine yardımcı olması ve sembolleri koruması için ipucu olarak kullanılıyor..."
            elif srt_file_path_str:
                parsed_srt_text = self.parse_srt_for_text(srt_file_path_str)
                if parsed_srt_text:
                    initial_prompt_for_model = parsed_srt_text
                    prompt_source_status = "SRT metni (doğruluk için referans olarak) kullanılıyor..."
                elif specific_initial_prompt: 
                    initial_prompt_for_model = specific_initial_prompt
                    prompt_source_status = "İlk ipucu metni kullanılıyor (SRT seçildi ama okunamadı)..."
            elif specific_initial_prompt:
                initial_prompt_for_model = specific_initial_prompt
                prompt_source_status = "İlk ipucu metni kullanılıyor..."
            
            self.status.set(prompt_source_status)
            self.root.update()
            
            # Transkripsiyonu başlat
            segments, info = model.transcribe(
                self.audio_path.get(),
                beam_size=self.beam_size.get(),
                language=language,
                temperature=self.temperature.get(),
                initial_prompt=initial_prompt_for_model,
                word_timestamps=self.word_timestamps.get(),
                vad_filter=self.vad_filter.get(),
                vad_parameters={"threshold": self.vad_threshold.get()} if self.vad_filter.get() else None
            )
            end_time = time.time() # Record end time
            transcription_time = round(end_time - start_time, 2) # Calculate duration
            
            # Sonuçları topla
            word_timings = []
            for segment in segments:
                if self.word_timestamps.get():
                    for word in segment.words:
                        word_timings.append({
                            "text": word.word.strip(),
                            "start": round(word.start, 2),
                            "end": round(word.end, 2)
                        })
                else:
                    # Kelime zamanlamaları kapalıysa segment zamanlamalarını kullan
                    word_timings.append({
                        "text": segment.text.strip(),
                        "start": round(segment.start, 2),
                        "end": round(segment.end, 2)
                    })
            
            # JSON dosyasına kaydet
            with open(self.output_path.get(), "w", encoding="utf-8") as f:
                json.dump(word_timings, f, ensure_ascii=False, indent=2)
            
            self.status.set(f"Tamamlandı! Süre: {transcription_time} saniye. Zamanlı metin listesi kaydedildi: {self.output_path.get()}")
            messagebox.showinfo("Başarılı", f"Transkripsiyon {transcription_time} saniyede tamamlandı ve sonuçlar kaydedildi.")
            
        except Exception as e:
            messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu: {str(e)}")
            self.status.set("Hata oluştu")


if __name__ == "__main__":
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()
