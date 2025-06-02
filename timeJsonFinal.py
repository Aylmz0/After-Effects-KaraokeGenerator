from faster_whisper import WhisperModel
import json
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import time
import string # Ensure string is imported
import re
from thefuzz import fuzz
import threading # Threading için eklendi
import traceback # Hata ayıklama ve detaylı hata mesajları için eklendi

try:
    import torch
    TORCH_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False

class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Faster Whisper Arayüzü")
        self.root.geometry("650x700")
        self.root.resizable(True, True)
        
        # Model ve parametreleri için önbellek
        self.model = None
        self.current_model_params = {}

        # Değişkenler
        self.audio_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.srt_path = tk.StringVar() # For optional SRT file input
        self.model_size = tk.StringVar(value="medium")  # Türkçe için medium daha iyi
        self.selected_device = tk.StringVar() # For CPU/GPU selection
        
        # Gelişmiş ayarlar için değişkenler
        self.language = tk.StringVar(value="tr")  # Türkçe varsayılan
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.IntVar(value=5)
        self.vad_filter = tk.BooleanVar(value=False) # VAD filtresi varsayılan olarak kapalı
        self.vad_threshold = tk.DoubleVar(value=0.0) # VAD eşiği varsayılan olarak 0.0
        self.temperature = tk.DoubleVar(value=0.0)
        self.initial_prompt = tk.StringVar(value="")
        self.word_timestamps = tk.BooleanVar(value=True)
        
        # Eşik değerleri için değişkenler (Düzeltme Aracı)
        self.primary_threshold_var = tk.DoubleVar(value=70.0)
        self.context_threshold_var = tk.DoubleVar(value=85.0)
        self.key_relaxed_threshold_var = tk.DoubleVar(value=40.0)
        
        # Düzeltme Aracı için iş parçacığı yönetimi
        self.correction_thread = None # Aktif düzeltme iş parçacığını tutar

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
        
        ttk.Label(main_frame, text="İşlem Birimi:").grid(column=0, row=11, sticky="w", pady=5)
        self.device_combobox = ttk.Combobox(main_frame, textvariable=self.selected_device, state="readonly")
        self.device_combobox.grid(column=0, row=12, sticky="ew")
        
        ttk.Separator(main_frame, orient="horizontal").grid(column=0, row=13, columnspan=2, sticky="ew", pady=15)
        
        # Tam metin ipucu (prompt) alanı
        ttk.Label(main_frame, text="Tam Metin (Doğruluğu Arttırır):").grid(column=0, row=14, sticky="w", pady=5)
        ttk.Label(main_frame, text="Ses kaydının tam metnini biliyorsanız, buraya yapıştırın:").grid(column=0, row=15, sticky="w", pady=(0,5))
        self.full_text_prompt = scrolledtext.ScrolledText(main_frame, width=50, height=6, wrap=tk.WORD)
        self.full_text_prompt.grid(column=0, row=16, columnspan=2, sticky="ew", pady=5)
        
        # İşlem butonu
        self.transcribe_button = ttk.Button(main_frame, text="Transkripsiyon Başlat", command=self.run_transcription)
        self.transcribe_button.grid(column=0, row=17, columnspan=2, pady=20)
        
        # Durum göstergesi
        self.status = tk.StringVar(value="Hazır")
        ttk.Label(main_frame, textvariable=self.status).grid(column=0, row=18, columnspan=2)
        
        # İşlemci Kullanım Bilgisi
        self.device_info_label = ttk.Label(main_frame, text="Kullanılan İşlemci: CPU (değiştirilemez)")
        self.device_info_label.grid(column=0, row=19, columnspan=2, sticky="w", pady=(5,0))
        
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
        vad_scale_frame = ttk.Frame(advanced_frame) # Frame for scale and label
        vad_scale_frame.grid(column=1, row=6, sticky="ew", padx=10)
        vad_scale = ttk.Scale(vad_scale_frame, from_=0.0, to=0.9, orient="horizontal", variable=self.vad_threshold, command=self._update_vad_label)
        vad_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.vad_value_label = ttk.Label(vad_scale_frame, text=f"{self.vad_threshold.get():.1f}")
        self.vad_value_label.pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(advanced_frame, text="(Daha düşük değer daha fazla sesi algılar, yüksek değer daha seçicidir)").grid(column=0, row=7, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Temperature:").grid(column=0, row=8, sticky="w", pady=5)
        temp_scale_frame = ttk.Frame(advanced_frame) # Frame for scale and label
        temp_scale_frame.grid(column=1, row=8, sticky="ew", padx=10)
        temp_scale = ttk.Scale(temp_scale_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.temperature, command=self._update_temp_label)
        temp_scale.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.temp_value_label = ttk.Label(temp_scale_frame, text=f"{self.temperature.get():.1f}")
        self.temp_value_label.pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(advanced_frame, text="(0: en olası sonuç, yüksek değer: daha yaratıcı sonuçlar)").grid(column=0, row=9, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="İlk İpucu Metni:").grid(column=0, row=10, sticky="w", pady=5)
        ttk.Entry(advanced_frame, width=40, textvariable=self.initial_prompt).grid(column=1, row=10, sticky="ew", padx=10)
        ttk.Label(advanced_frame, text="(Modele başlangıç ipucu, 'Bu bir Türkçe konuşma kaydıdır' gibi)").grid(column=0, row=11, columnspan=2, sticky="w", pady=(0,5))
        
        ttk.Label(advanced_frame, text="Kelime Zamanlamaları:").grid(column=0, row=12, sticky="w", pady=5)
        ttk.Checkbutton(advanced_frame, variable=self.word_timestamps).grid(column=1, row=12, sticky="w", padx=10)
        ttk.Label(advanced_frame, text="(Her kelime için ayrı zaman bilgisi, kapalıysa cümle zamanları)").grid(column=0, row=13, columnspan=2, sticky="w", pady=(0,5))
        
        # Türkçe için öneriler
        ttk.Separator(advanced_frame, orient="horizontal").grid(column=0, row=18, columnspan=3, sticky="ew", pady=15)
        ttk.Label(advanced_frame, text="Türkçe İçin Önerilen Ayarlar", font=("", 10, "bold")).grid(column=0, row=19, columnspan=3, sticky="w", pady=5)
        ttk.Label(advanced_frame, text="- Medium veya Large model kullanın").grid(column=0, row=20, columnspan=3, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- VAD filtresi açık olmalı").grid(column=0, row=21, columnspan=3, sticky="w", pady=2)
        ttk.Label(advanced_frame, text="- Beam Size 5 ideal").grid(column=0, row=22, columnspan=3, sticky="w", pady=2)
        
        # Varsayılan ayarları yükle butonu
        self.load_defaults_button = ttk.Button(advanced_frame, text="Türkçe İçin Varsayılanları Yükle", command=self.load_turkish_defaults)
        self.load_defaults_button.grid(column=0, row=23, columnspan=3, pady=20)
        
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
        self._initialize_device_selection() # Initialize device options
        self._update_vad_label() # Initial update for VAD label
        self._update_temp_label() # Initial update for Temperature label
    
    def _initialize_device_selection(self):
        devices = ["CPU"]
        initial_status = "Hazır"
        default_device = "CPU"

        if TORCH_AVAILABLE and CUDA_AVAILABLE:
            devices.append("GPU (CUDA)")
            initial_status = "Hazır (CUDA Kullanılabilir)"
            default_device = "GPU (CUDA)" # Default to GPU if available
        elif not TORCH_AVAILABLE:
            initial_status = "Hazır (PyTorch kurulu değil, sadece CPU kullanılabilir)"
        elif not CUDA_AVAILABLE:
            initial_status = "Hazır (CUDA bulunamadı, sadece CPU kullanılabilir)"

        self.device_combobox['values'] = devices
        self.selected_device.set(default_device)
        self.status.set(initial_status)

    def _update_vad_label(self, event=None):
        self.vad_value_label.config(text=f"{self.vad_threshold.get():.1f}")

    def _update_temp_label(self, event=None):
        self.temp_value_label.config(text=f"{self.temperature.get():.1f}")
    
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
        
        ttk.Button(control_buttons_frame, text="Dosyaları Yükle ve Görüntüle", command=self._start_correction_with_thresholds).pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(control_buttons_frame, text="Düzeltilmiş JSON'u Kaydet", command=self._save_corrected_json).pack(side=tk.LEFT)

        # Eşik Değerleri Ayar Bölümü
        threshold_settings_frame = ttk.LabelFrame(self.correction_frame, text="Eşik Değerleri (%)", padding="10")
        threshold_settings_frame.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Primary Threshold
        ttk.Label(threshold_settings_frame, text="3/3 Eşleşme (Ana):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        primary_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.primary_threshold_var, length=150,
                                  command=lambda v: self.primary_threshold_val_label.config(text=f"{float(v):.0f}%"))
        primary_scale.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.primary_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.primary_threshold_var.get():.0f}%")
        self.primary_threshold_val_label.grid(row=0, column=2, sticky="w", padx=5, pady=2)

        # Context Threshold
        ttk.Label(threshold_settings_frame, text="P/N Bağlam (2.5 Eşl.):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        context_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.context_threshold_var, length=150,
                                  command=lambda v: self.context_threshold_val_label.config(text=f"{float(v):.0f}%"))
        context_scale.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.context_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.context_threshold_var.get():.0f}%")
        self.context_threshold_val_label.grid(row=1, column=2, sticky="w", padx=5, pady=2)

        # Key Relaxed Threshold
        ttk.Label(threshold_settings_frame, text="Anahtar K. Esnek (2.5 Eşl.):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        key_relaxed_scale = ttk.Scale(threshold_settings_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.key_relaxed_threshold_var, length=150,
                                      command=lambda v: self.key_relaxed_threshold_val_label.config(text=f"{float(v):.0f}%"))
        key_relaxed_scale.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.key_relaxed_threshold_val_label = ttk.Label(threshold_settings_frame, text=f"{self.key_relaxed_threshold_var.get():.0f}%")
        self.key_relaxed_threshold_val_label.grid(row=2, column=2, sticky="w", padx=5, pady=2)

        # Text Display Areas
        display_frame = ttk.LabelFrame(self.correction_frame, text="Dosya İçerikleri", padding="10")
        display_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="nsew")
        
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(1, weight=1) 

        ttk.Label(display_frame, text="Referans TXT İçeriği:").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        self.txt_correction_display_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=15)
        self.txt_correction_display_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        ttk.Label(display_frame, text="JSON İçeriği (Düzeltilecek):").grid(row=0, column=1, sticky="w", padx=5, pady=(5,0))
        self.json_correction_display_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, height=15)
        self.json_correction_display_area.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.correction_frame.rowconfigure(6, weight=1) 
        self.correction_frame.columnconfigure(0, weight=1)

    def _clean_for_compare(self, text):
        original_for_debug = str(text)

        # Turkish-specific character handling for lowercase
        text_lower = str(text).replace('İ', 'i').replace('I', 'ı').lower()

        # Characters to remove using Unicode escape sequences for reliability
        bullet_circle = "\u25cf"      # ●
        bullet_triangle = "\u25ba"    # ►
        bullet_dot = "\u2022"         # •
        left_double_quote = "\u201c"  # “
        right_double_quote = "\u201d" # ”
        left_single_quote = "\u2018"  # ‘
        right_single_quote = "\u2019" # ’ 
        ellipsis = "\u2026"     # …
        en_dash = "\u2013"       # –
        em_dash = "\u2014"       # —

        punctuation_to_remove_explicitly = (
            bullet_circle + bullet_triangle + bullet_dot +
            left_double_quote + right_double_quote +
            left_single_quote + right_single_quote +
            ellipsis + en_dash + em_dash
        )
        
        all_punctuation_to_remove = string.punctuation + punctuation_to_remove_explicitly
        
        # Aynı karakterlerin birden fazla olmasını engellemek için benzersiz hale getir
        unique_chars_to_remove = "".join(sorted(list(set(all_punctuation_to_remove))))
                                            
        translator = str.maketrans('', '', unique_chars_to_remove)
        text_no_punct = text_lower.translate(translator)
        
        # Remove all whitespace (spaces, tabs, newlines etc.) by splitting (defaults to any whitespace) and joining
        cleaned_text = " ".join(text_no_punct.split())
        
        print(f"DBG Clean: Original='{original_for_debug}' -> Cleaned='{cleaned_text}' (Temizlenen Karakterler Listesi: '{unique_chars_to_remove}')")
        print(f"DEBUG CleanOutput: '{cleaned_text}' (From Original: '{original_for_debug}')")
        return cleaned_text

    def _start_correction_with_thresholds(self):
        if self.correction_thread and self.correction_thread.is_alive():
            messagebox.showinfo("Bilgi", "Zaten devam eden bir düzeltme işlemi var.")
            return

        self._toggle_ui_elements_for_correction_tool(True)
        self._update_status("Düzeltme ayarları okunuyor...")

        try:
            primary_thresh = int(self.primary_threshold_var.get())
            context_thresh = int(self.context_threshold_var.get())
            key_relaxed_thresh = int(self.key_relaxed_threshold_var.get())
        except ValueError:
            self._show_correction_error_async("Eşik değerleri geçerli sayılar olmalıdır.")
            self._toggle_ui_elements_for_correction_tool(False)
            self._update_status("Hatalı eşik değeri girişi.")
            return

        # Create and start the correction thread
        self.correction_thread = threading.Thread(
            target=self._perform_correction_in_thread,
            args=(primary_thresh, context_thresh, key_relaxed_thresh),
            daemon=True  # Daemon thread will exit when the main program exits
        )
        self.correction_thread.start()
        self._update_status("Düzeltme işlemi başlatılıyor...") # Initial status update

    def _load_files_for_correction(self, primary_threshold, context_threshold, key_relaxed_threshold):
        json_path_str = self.correction_json_path.get()
        txt_path_str = self.correction_txt_path.get()

        if not json_path_str or not txt_path_str:
            self.root.after(0, self._show_correction_error_async, "Lütfen hem JSON hem de TXT dosyalarını seçin.")
            return False # Indicate failure

        self.unmatched_log_entries = [] # Eşleşmeyen log girdileri için liste

        try:
            self.root.after(0, self._update_status, "JSON ve TXT dosyaları okunuyor...")
            with open(json_path_str, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    self.current_correction_data = []
                    for item in loaded_data:
                        if isinstance(item, dict):
                            self.current_correction_data.append({k: v for k, v in item.items()})
                        elif isinstance(item, str):
                            self.current_correction_data.append({'text': item, 'words': [{'word': item, 'start': 0, 'end': 0}]})
                        else:
                            print(f"Uyarı: JSON içinde beklenmedik öğe türü: {type(item)}, atlanıyor.")
                elif isinstance(loaded_data, dict) and 'segments' in loaded_data:
                     self.current_correction_data = loaded_data['segments']
                else: 
                    self.root.after(0, self._show_correction_error_async, "JSON formatı beklenenden farklı. Segment listesi bekleniyor.")
                    return False

            with open(txt_path_str, 'r', encoding='utf-8') as f:
                self.txt_content_lines_for_correction = [str(line) for line in f.read().splitlines()]

            self.root.after(0, self._update_status, "Düzeltme Aracı Başlatılıyor... TXT işleniyor.")
            print("----- Düzeltme Aracı Başlatılıyor (Strateji v7: Gelişmiş Bağlam Eşleştirme) -----")
            print(f"JSON dosyasından {len(self.current_correction_data)} segment/öğe yüklendi.")
            print(f"TXT dosyasından {len(self.txt_content_lines_for_correction)} satır yüklendi.")

            bullet_chars_to_detect = ['●', '•', '►'] 
            txt_contexts = []

            print("\n----- TXT İşleniyor: Satır Bazlı Bağlam Oluşturuluyor (Revize Edilmiş) -----")
            # IMPORTANT: This is where your existing TXT processing loop should be.
            # The following is a placeholder for your actual TXT processing logic
            # that populates the 'txt_contexts' list. Ensure your original loop is here.
            # Example structure of what might be here (from previous views):
            for current_line_idx, raw_current_line in enumerate(self.txt_content_lines_for_correction):
                stripped_current_line = raw_current_line.lstrip()
                bullet_char_found_for_line = None
                text_after_bullet_on_line = ""
                for bc_candidate in bullet_chars_to_detect:
                    if stripped_current_line.startswith(bc_candidate):
                        bullet_char_found_for_line = bc_candidate
                        text_after_bullet_on_line = stripped_current_line[len(bc_candidate):].lstrip()
                        break
                if bullet_char_found_for_line and text_after_bullet_on_line:
                    words_after_bullet_original = text_after_bullet_on_line.split()
                    if not words_after_bullet_original: continue
                    original_key_text = words_after_bullet_original[0]
                    key_word = self._clean_for_compare(original_key_text)
                    key_word_base = None
                    if "'" in original_key_text or "\u2019" in original_key_text:
                        base_part = original_key_text.split("'", 1)[0].split("\u2019", 1)[0]
                        key_word_base = self._clean_for_compare(base_part)
                    prev_cleaned_word = "<NONE>"
                    strip_offset = raw_current_line.find(stripped_current_line)
                    text_before_bullet_char_on_current_line = raw_current_line[:strip_offset].strip()
                    if text_before_bullet_char_on_current_line:
                        words_before_bullet_cleaned = [self._clean_for_compare(w) for w in text_before_bullet_char_on_current_line.split() if self._clean_for_compare(w)]
                        if words_before_bullet_cleaned: prev_cleaned_word = words_before_bullet_cleaned[-1]
                    if prev_cleaned_word == "<NONE>":
                        for prev_line_search_idx in range(current_line_idx - 1, -1, -1):
                            prev_raw_line_content = self.txt_content_lines_for_correction[prev_line_search_idx]
                            prev_line_words_cleaned = [self._clean_for_compare(w) for w in prev_raw_line_content.strip().split() if self._clean_for_compare(w)]
                            if prev_line_words_cleaned: prev_cleaned_word = prev_line_words_cleaned[-1]; break
                    next_cleaned_word = "<NONE>"
                    if len(words_after_bullet_original) > 1:
                        next_word_on_same_line_original = words_after_bullet_original[1]
                        cleaned_candidate = self._clean_for_compare(next_word_on_same_line_original)
                        if cleaned_candidate: next_cleaned_word = cleaned_candidate
                    if next_cleaned_word == "<NONE>":
                        for next_line_search_idx in range(current_line_idx + 1, len(self.txt_content_lines_for_correction)):
                            # *** Correction for potentially incomplete line from previous views ***
                            if next_line_search_idx < len(self.txt_content_lines_for_correction):
                                next_raw_line_content = self.txt_content_lines_for_correction[next_line_search_idx]
                                next_line_words_cleaned = [self._clean_for_compare(w) for w in next_raw_line_content.strip().split() if self._clean_for_compare(w)]
                                if next_line_words_cleaned: next_cleaned_word = next_line_words_cleaned[0]; break
                            else: break # Safety break if index goes out of bounds
                    txt_contexts.append({'key': key_word, 'base_key': key_word_base, 'prev': prev_cleaned_word, 'next': next_cleaned_word, 'original_key': original_key_text, 'line_idx': current_line_idx})
            # --- END OF TXT PROCESSING LOOP (Assumed) ---
            print("\n----- TXT İşleme Tamamlandı. Oluşturulan TXT Bağlam Sayısı:", len(txt_contexts), "-----")

            # ----- NEW JSON PROCESSING AND LOGGING LOGIC -----
            print("\n----- JSON İşleniyor ve TXT ile Karşılaştırılıyor -----")
            if not self.current_correction_data or not isinstance(self.current_correction_data, list):
                print("Uyarı: İşlenecek JSON verisi bulunamadı veya formatı yanlış.")
            else:
                for i, json_segment in enumerate(self.current_correction_data):
                    if not isinstance(json_segment, dict) or 'words' not in json_segment or not isinstance(json_segment['words'], list):
                        current_json_word_text_original = json_segment.get('text', '').strip()
                        if not current_json_word_text_original: continue
                        words_to_process = [{'word': current_json_word_text_original, 'start': json_segment.get('start',0), 'end': json_segment.get('end',0)}]
                    else:
                        words_to_process = json_segment['words']

                    for word_idx, current_word_obj in enumerate(words_to_process):
                        current_json_word_text_original = current_word_obj.get('word', '')
                        current_json_word_text_cleaned = self._clean_for_compare(current_json_word_text_original)
                        if not current_json_word_text_cleaned: continue

                        prev_json_word_text_cleaned = "<YOK>"
                        if word_idx > 0: prev_json_word_text_cleaned = self._clean_for_compare(words_to_process[word_idx-1].get('word', ''))
                        elif i > 0 and isinstance(self.current_correction_data[i-1].get('words'), list) and self.current_correction_data[i-1]['words']:
                            prev_json_word_text_cleaned = self._clean_for_compare(self.current_correction_data[i-1]['words'][-1].get('word',''))

                        next_json_word_text_cleaned = "<YOK>"
                        if word_idx < len(words_to_process) - 1: next_json_word_text_cleaned = self._clean_for_compare(words_to_process[word_idx+1].get('word', ''))
                        elif i < len(self.current_correction_data) - 1 and isinstance(self.current_correction_data[i+1].get('words'), list) and self.current_correction_data[i+1]['words']:
                            next_json_word_text_cleaned = self._clean_for_compare(self.current_correction_data[i+1]['words'][0].get('word',''))
                        
                        best_match_score = 0
                        best_txt_context = None
                        
                        if not txt_contexts:
                            log_entry = (f"Current Word (JSON): {current_json_word_text_original} (Prev JSON: {prev_json_word_text_cleaned}, Next JSON: {next_json_word_text_cleaned}) "
                                         f"--- TXT Bağlamı Bulunamadı (TXT Contexts Listesi Boş)")
                            self.unmatched_log_entries.append(log_entry)
                            continue

                        for txt_context_candidate in txt_contexts:
                            score = fuzz.ratio(current_json_word_text_cleaned, txt_context_candidate['key'])
                            if txt_context_candidate.get('base_key'): # Check base form if available
                                score = max(score, fuzz.ratio(current_json_word_text_cleaned, txt_context_candidate['base_key']))
                            if score > best_match_score:
                                best_match_score = score
                                best_txt_context = txt_context_candidate
                    
                        log_this_entry = False
                        match_status_for_log = f"Anahtar Eşleşme: {best_match_score}%"

                        if best_match_score < primary_threshold:
                            log_this_entry = True
                            match_status_for_log += " (DÜŞÜK)"
                    
                        if log_this_entry and best_txt_context:
                            prev_txt_key = best_txt_context.get('prev', '<TXTYOK>')
                            next_txt_key = best_txt_context.get('next', '<TXTYOK>')
                            prev_json_to_txt_score = fuzz.ratio(prev_json_word_text_cleaned, prev_txt_key) if prev_json_word_text_cleaned != "<YOK>" and prev_txt_key != "<TXTYOK>" else 0
                            next_json_to_txt_score = fuzz.ratio(next_json_word_text_cleaned, next_txt_key) if next_json_word_text_cleaned != "<YOK>" and next_txt_key != "<TXTYOK>" else 0
                            prev_status_log = "Eşleşmedi" if prev_json_to_txt_score < context_threshold else "Eşleşti"
                            next_status_log = "Eşleşmedi" if next_json_to_txt_score < context_threshold else "Eşleşti"

                            log_entry = (f"Current Word (JSON): {current_json_word_text_original} (Prev JSON: {prev_json_word_text_cleaned}, Next JSON: {next_json_word_text_cleaned}) "
                                         f"--- En Yakın TXT Bağlamı (Orijinal Anahtar: {best_txt_context.get('original_key', '<ANAHTARYOK>')}, {match_status_for_log}): "
                                         f"Previous Key (TXT): {prev_txt_key} (JSON ile: {prev_status_log} - {prev_json_to_txt_score}%), "
                                         f"Next Key (TXT): {next_txt_key} (JSON ile: {next_status_log} - {next_json_to_txt_score}%)")
                            self.unmatched_log_entries.append(log_entry)
                        elif log_this_entry and not best_txt_context:
                             log_entry = (f"Current Word (JSON): {current_json_word_text_original} (Prev JSON: {prev_json_word_text_cleaned}, Next JSON: {next_json_word_text_cleaned}) "
                                          f"--- TXT Bağlamı Bulunamadı (Hiçbiriyle Eşleşmedi)")
                             self.unmatched_log_entries.append(log_entry)
        # ----- END OF JSON PROCESSING AND LOGGING LOGIC -----
    
            self.root.after(0, self.update_correction_text_display) 
            self.root.after(0, self.update_status_correction, "Dosyalar yüklendi. Eşleşmeler kontrol edildi. Gerekirse düzenleyip kaydedin.")
            return True 

        except FileNotFoundError as e:
            self.root.after(0, self._show_correction_error_async, f"Dosya bulunamadı: {e}")
            self.root.after(0, self._update_status, "Hata: Dosya bulunamadı.")
            return False
        except json.JSONDecodeError as e:
            self.root.after(0, self._show_correction_error_async, f"JSON dosyası okunurken hata: {e}")
            self.root.after(0, self._update_status, "Hata: JSON formatı bozuk.")
            return False
        except Exception as e:
            detailed_error = traceback.format_exc()
            error_msg = f"Dosyalar işlenirken beklenmedik bir hata oluştu: {e}"
            print(f"{error_msg}\n{detailed_error}") 
            self.root.after(0, self._show_correction_error_async, error_msg)
            self.root.after(0, self._update_status, "Hata: Dosya işleme hatası.")
            return False

    def update_correction_text_display(self):
        """Düzeltme Aracı sekmesindeki JSON ve TXT metin alanlarını günceller."""
        # JSON metin alanını güncelle
        self.json_correction_display_area.config(state="normal")
        self.json_correction_display_area.delete("1.0", tk.END)
        if self.current_correction_data:
            for item in self.current_correction_data:
                self.json_correction_display_area.insert(tk.END, str(item.get('text', '')) + '\n')
        # self.json_correction_display_area.config(state="disabled") # Kullanıcı düzenleyebilmeli

        # TXT metin alanını güncelle
        self.txt_correction_display_area.config(state="normal")
        self.txt_correction_display_area.delete("1.0", tk.END)
        if hasattr(self, 'txt_content_lines_for_correction') and self.txt_content_lines_for_correction:
            for line in self.txt_content_lines_for_correction:
                self.txt_correction_display_area.insert(tk.END, str(line) + '\n')
        self.txt_correction_display_area.config(state="disabled") # TXT salt okunur kalmalı

    def update_status_correction(self, message: str):
        """Düzeltme Aracı için durum mesajını ayarlar (ana durum etiketini kullanır)."""
        self.status.set(message) # Ana durum etiketini kullan

    def _save_corrected_json(self):
        if not self.current_correction_data:
            messagebox.showwarning("Veri Yok", "Önce JSON verisini yükleyin ve düzenleyin.")
            return

        edited_lines = self.json_correction_display_area.get("1.0", tk.END).strip().split('\n')
        
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
            # Fix: Düzelt metinlerdeki çift-kaçışlı yeni satır karakterlerini (\\n -> \n)
            for item in self.current_correction_data:
                if isinstance(item, dict) and 'text' in item and isinstance(item['text'], str):
                    # Eğer text içinde "\n" varsa "\n"'e çevir
                    if '\\n' in item['text']:
                        item['text'] = item['text'].replace('\\n', '\n')
    
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.current_correction_data, f, ensure_ascii=False, indent=2)
        
            # ----- YENİ EKLENEN LOG KAYDETME MANTIĞI -----
            log_message_for_popup = f"{updated_count} öğe güncellenerek düzeltilmiş JSON dosyası kaydedildi: {save_path}"
            if hasattr(self, 'unmatched_log_entries') and self.unmatched_log_entries:
                log_file_path = os.path.join(os.path.dirname(save_path), "unmatched_log.txt")
                try:
                    with open(log_file_path, 'w', encoding='utf-8') as log_f:
                        log_f.write("Eşleşmeyen Kelimeler İçin Loglar:\n")
                        log_f.write("=====================================\n")
                        for entry in self.unmatched_log_entries:
                            log_f.write(f"{entry}\n")
                    log_message_for_popup += f"\nEşleşmeyen kelimeler için log dosyası oluşturuldu: {log_file_path}"
                    print(f"Eşleşmeyen kelimeler log dosyasına yazıldı: {log_file_path}")
                except Exception as log_e:
                    log_message_for_popup += f"\nUYARI: Eşleşmeyenler için log dosyası oluşturulamadı: {log_e}"
                    print(f"HATA: unmatched_log.txt dosyası oluşturulurken/yazılırken hata: {log_e}")
            # ----- LOG KAYDETME MANTIĞI SONU -----

            messagebox.showinfo("Başarılı", log_message_for_popup) # Güncellenmiş mesaj
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
        self._update_vad_label() # Update label after loading defaults
        self._update_temp_label() # Update label after loading defaults
    
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
        if not self.audio_path.get() or not self.output_path.get():
            messagebox.showerror("Hata", "Lütfen ses dosyası ve çıktı konumu seçin.")
            return
        
        # Ayarları topla ve onay mesajını oluştur
        settings_summary = f"""Seçilen Ayarlar:
        Model Boyutu: {self.model_size.get()}
        Dil: {self.language.get()}
        Cihaz: {self.selected_device.get()}
        Hesaplama Türü: {self.compute_type.get()}
        Beam Size: {self.beam_size.get()}
        VAD Filtresi: {'Aktif' if self.vad_filter.get() else 'Pasif'} (Eşik: {self.vad_threshold.get() if self.vad_filter.get() else 'N/A'})
        Sıcaklık: {self.temperature.get()}
        Kelime Zaman Damgaları: {'Evet' if self.word_timestamps.get() else 'Hayır'}
        Başlangıç Metni: '{self.initial_prompt.get() if self.initial_prompt.get() else 'Yok'}'
        SRT Dosyası: '{self.srt_path.get() if self.srt_path.get() else 'Yok'}'

        Transkripsiyonu bu ayarlarla başlatmak istediğinize emin misiniz?
        """

        if not messagebox.askyesno("Transkripsiyonu Başlat Onayı", settings_summary):
            self._update_status_safe("Transkripsiyon kullanıcı tarafından iptal edildi.")
            return # Kullanıcı iptal etti
        
        self._toggle_ui_elements_for_transcription(enable=False)
        self._update_status_safe("Transkripsiyon iş parçacığı başlatılıyor...")

        # Transkripsiyon işlemini ayrı bir thread'de başlat
        transcription_thread = threading.Thread(target=self._perform_transcription_logic)
        transcription_thread.daemon = True # Ana program kapanınca thread'in de kapanmasını sağlar
        transcription_thread.start()

    def _perform_transcription_logic(self):
        try:
            start_time = time.time() # Record start time

            # Cihaz seçimini kontrol et
            actual_device_to_use = "cuda" if self.selected_device.get() == "GPU (CUDA)" and CUDA_AVAILABLE else "cpu"
            
            # Dil ayarını kontrol et
            language = self.language.get() if self.language.get() else None # None ise otomatik dil tespiti

            # Model Önbellekleme Mantığı
            new_model_params = {
                "model_size": self.model_size.get(),
                "device": actual_device_to_use,
                "compute_type": self.compute_type.get()
            }

            model_loaded_successfully = False
            if self.model is None or self.current_model_params != new_model_params:
                if self.model is not None and self.current_model_params.get('device') == 'cuda':
                    self._update_status_safe("Mevcut CUDA modeli bellekten kaldırılıyor...")
                    del self.model # Modeli sil
                    if TORCH_AVAILABLE and CUDA_AVAILABLE: # torch.cuda.empty_cache() için kontrol
                        torch.cuda.empty_cache()
                    self.model = None # Silindikten sonra None olarak ayarla
                
                self._update_status_safe(f"Model yükleniyor: {new_model_params['model_size']} ({new_model_params['device'].upper()}, {new_model_params['compute_type']})...")
                try:
                    self.model = WhisperModel(
                        new_model_params['model_size'],
                        device=new_model_params['device'],
                        compute_type=new_model_params['compute_type']
                    )
                    self.current_model_params = new_model_params
                    self._update_status_safe(f"Model başarıyla yüklendi: {new_model_params['model_size']}")
                    model_loaded_successfully = True
                except Exception as model_load_error:
                    self._show_messagebox_safe("error", "Model Yükleme Hatası", f"Model yüklenirken bir hata oluştu: {str(model_load_error)}")
                    self._update_status_safe("Model yükleme hatası!")
                    self.model = None # Başarısız yükleme durumunda modeli None yap
                    self.current_model_params = {} # Parametreleri de sıfırla
                    self._toggle_ui_elements_for_transcription(enable=True) # Butonları tekrar aktif et
                    return # Model yüklenemezse transkripsiyona devam etme
            else:
                self._update_status_safe(f"Önbellekten model kullanılıyor: {self.model_size.get()} ({actual_device_to_use.upper()})...")
                model_loaded_successfully = True # Model zaten yüklü ve geçerli
            
            if not model_loaded_successfully or self.model is None:
                self._show_messagebox_safe("error", "Hata", "Transkripsiyon için model mevcut değil veya yüklenemedi.")
                self._update_status_safe("Model hatası!")
                self._toggle_ui_elements_for_transcription(enable=True)
                return

            # SRT dosyasından metin okuma ve prompt hazırlama
            initial_prompt_for_model = "" # Model için kullanılacak nihai prompt
            prompt_source_status = "İlk ipucu için kaynak belirleniyor..."
            
            specific_initial_prompt = self.full_text_prompt.get("1.0", tk.END).strip()
            srt_file_path = self.srt_path.get()

            if srt_file_path: # Eğer bir SRT dosyası seçilmişse
                parsed_srt_text = self.parse_srt_for_text(srt_file_path)
                if parsed_srt_text: # SRT'den metin başarıyla okunmuşsa
                    processed_lines = []
                    current_line_group = []
                    for line in parsed_srt_text.split('\n'):
                        stripped_line = line.strip()
                        if stripped_line:
                            current_line_group.append(stripped_line)
                        elif current_line_group: # Boş satır ve grup doluysa, grubu işle
                            processed_lines.append(" ".join(current_line_group))
                            current_line_group = []
                    if processed_lines:
                        initial_prompt_for_model = "".join([f"\n{item_line}" for item_line in processed_lines])
                    else:
                        initial_prompt_for_model = ""
                    prompt_source_status = "SRT metni (doğruluk için referans olarak) kullanılıyor..."
                elif specific_initial_prompt: 
                    initial_prompt_for_model = specific_initial_prompt
                    prompt_source_status = "İlk ipucu metni kullanılıyor (SRT seçildi ama okunamadı veya boş)..."
                else:
                    prompt_source_status = "SRT dosyası okunamadı veya boş, ipucu kullanılmıyor."
            elif specific_initial_prompt: # Eğer SRT dosyası seçilmemişse AMA kullanıcı ipucu metni girdiyse
                initial_prompt_for_model = specific_initial_prompt
                prompt_source_status = "İlk ipucu metni kullanılıyor..."
            else: # Ne SRT ne de kullanıcı ipucu metni yoksa
                prompt_source_status = "İpucu metni veya SRT dosyası sağlanmadı."
            
            self._update_status_safe(prompt_source_status)
            
            # Transkripsiyonu başlat
            self._update_status_safe(f"Transkripsiyon başlıyor ({actual_device_to_use.upper()})...")
            segments, info = self.model.transcribe(
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
                            "text": str(word.word).strip(),
                            "start": round(word.start, 2),
                            "end": round(word.end, 2)
                        })
                else:
                    word_timings.append({
                        "text": str(segment.text).strip(),
                        "start": round(segment.start, 2),
                        "end": round(segment.end, 2)
                    })
            
            # JSON dosyasına kaydet
            with open(self.output_path.get(), "w", encoding="utf-8") as f:
                json.dump(word_timings, f, ensure_ascii=False, indent=2)
            
            final_message = f"Tamamlandı! ({actual_device_to_use.upper()}) Süre: {transcription_time} saniye. Zamanlı metin listesi kaydedildi: {self.output_path.get()}"
            self._update_status_safe(final_message)
            self._show_messagebox_safe("info", "Başarılı", f"Transkripsiyon ({actual_device_to_use.upper()}) {transcription_time} saniyede tamamlandı ve sonuçlar kaydedildi.")
            
        except Exception as e:
            error_message = f"İşlem sırasında bir hata oluştu: {str(e)}"
            self._show_messagebox_safe("error", "Hata", error_message)
            self._update_status_safe("Hata oluştu")
        finally:
            # İşlem bittiğinde veya hata oluştuğunda UI elemanlarını tekrar aktif et
            self._toggle_ui_elements_for_transcription(enable=True)


    def _update_status_safe(self, message):
        self.root.after(0, lambda: self.status.set(message))

    def _show_messagebox_safe(self, msg_type, title, message):
        if msg_type == "error":
            self.root.after(0, lambda: messagebox.showerror(title, message))
        elif msg_type == "info":
            self.root.after(0, lambda: messagebox.showinfo(title, message))
        elif msg_type == "warning":
            self.root.after(0, lambda: messagebox.showwarning(title, message))

    def _toggle_ui_elements_for_transcription(self, enable=True):
        state = tk.NORMAL if enable else tk.DISABLED
        self.transcribe_button.config(state=state)
        self.load_defaults_button.config(state=state)
        # Diğer devre dışı bırakılacak/etkinleştirilecek elemanlar buraya eklenebilir
        # Örneğin, model seçimi, dosya seçimi butonları vs.
        self.device_combobox.config(state="readonly" if enable else tk.DISABLED) 
        # Combobox'lar için state="readonly" veya state=tk.NORMAL kullanılır, tk.DISABLED yerine.
        # Eğer Combobox'ın tamamen değiştirilemez olmasını istiyorsanız, state="disabled" kullanılabilir.
        # Ancak, kullanıcıya mevcut seçimi göstermeye devam etmek için "readonly" daha iyi olabilir.
        # Burada basitlik adına transcribe_button'ı devre dışı bırakıyoruz.

    def _toggle_ui_elements_for_correction_tool(self, is_running):
        """Toggles the state of UI elements based on whether the correction tool is running."""
        state = tk.DISABLED if is_running else tk.NORMAL
        # Assuming you have these buttons and entry fields, adjust as necessary
        # We will need to confirm the actual names of these UI elements later
        if hasattr(self, 'correction_start_button'): # Placeholder name
            self.correction_start_button.config(state=state)
        if hasattr(self, 'correction_json_entry'): # Placeholder name
            self.correction_json_entry.config(state=state)
        if hasattr(self, 'correction_txt_entry'): # Placeholder name
            self.correction_txt_entry.config(state=state)
        if hasattr(self, 'load_json_button_correction'): # Placeholder name
            self.load_json_button_correction.config(state=state)
        if hasattr(self, 'load_txt_button_correction'): # Placeholder name
            self.load_txt_button_correction.config(state=state)
        
        # Example of how you might disable other specific widgets if they exist
        # Check for the existence of these widgets before attempting to configure them
        # to avoid AttributeError if they are not defined in all contexts where this method might be called.
        widgets_to_toggle = [
            getattr(self, 'diarize_button', None),
            getattr(self, 'transcribe_button', None),
            getattr(self, 'diarize_and_transcribe_button', None),
            getattr(self, 'start_button', None), # Main start button for transcription/diarization
            getattr(self, 'file_entry', None),
            getattr(self, 'model_size_menu', None),
            getattr(self, 'language_menu', None),
            getattr(self, 'device_menu', None),
            getattr(self, 'compute_type_menu', None),
            getattr(self, 'initial_prompt_entry', None),
            getattr(self, 'hf_token_entry', None),
            getattr(self, 'min_speakers_entry', None),
            getattr(self, 'max_speakers_entry', None)
        ]

        for widget in widgets_to_toggle:
            if widget:
                widget.config(state=state)

    def _show_correction_error_async(self, message):
        """Shows an error message box from the main thread."""
        messagebox.showerror("Hata", message)

    def _perform_correction_in_thread(self, primary_threshold, context_threshold, key_relaxed_threshold):
        """Worker function to perform correction logic in a separate thread."""
        try:
            self.root.after(0, self._update_status, "Düzeltme işlemi arka planda çalışıyor...")
            
            # _load_files_for_correction will be modified to fit this threaded model
            # and to perform the entire correction or prepare for subsequent steps.
            success = self._load_files_for_correction(primary_threshold, context_threshold, key_relaxed_threshold)
            
            if success:
                # If _load_files_for_correction handles the entire process and returns true on overall success:
                self.root.after(0, self._update_status, "Düzeltme işlemi başarıyla tamamlandı.")
            else:
                # If _load_files_for_correction returns false, it means an early exit (e.g., file not found),
                # and it should have already scheduled an error message.
                self.root.after(0, self._update_status, "Düzeltme işlemi sonlandırıldı (detaylar için önceki mesajlara bakın).")

        except Exception as e:
            detailed_error = traceback.format_exc()
            print(f"Düzeltme aracı (thread) hatası: {e}\n{detailed_error}") # Log to console for debugging
            self.root.after(0, self._show_correction_error_async, f"Düzeltme sırasında beklenmedik bir hata oluştu: {e}")
            self.root.after(0, self._update_status, "Düzeltme işlemi bir hatayla durduruldu.")
        finally:
            # Re-enable UI elements and clear thread reference, ensuring this runs on the main thread
            self.root.after(0, self._toggle_ui_elements_for_correction_tool, False)
            self.root.after(0, lambda: setattr(self, 'correction_thread', None))

    def _update_status(self, message):
        self.status.set(message)

if __name__ == "__main__":
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()
