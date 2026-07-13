import cv2
import numpy as np
import time

class DactylHUD:
    """
    Modern & Minimalist HUD Renderer untuk Dactyl-AI Magic Cursor (run_system.py).
    Menggantikan antarmuka teks konvensional dengan Glassmorphic Panel, Rounded Badges,
    dan Hologram Keyboard futuristik yang bersih dan elegan.
    """
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_bold = cv2.FONT_HERSHEY_DUPLEX
        
        # Palet Warna Cyber Minimalist (BGR format untuk OpenCV)
        self.COLOR_BG_DARK = (24, 16, 10)       # #0a1018 Dark Slate blue-ish
        self.COLOR_BG_CARD = (35, 25, 16)       # Glass card background
        self.COLOR_CYAN = (255, 212, 0)         # #00d4ff Neon Cyan
        self.COLOR_EMERALD = (136, 255, 0)      # #00ff88 Emerald Green
        self.COLOR_CORAL = (107, 107, 255)      # #ff6b6b Coral Red
        self.COLOR_GOLD = (0, 184, 255)         # #ffb800 Gold
        self.COLOR_PURPLE = (239, 36, 178)      # #b224ef Cyber Purple
        self.COLOR_TEXT = (240, 244, 248)       # White/Silver Text
        self.COLOR_MUTED = (148, 163, 184)      # Muted Gray
        self.COLOR_BORDER = (80, 70, 55)        # Subtle Border

    def draw_rounded_rect(self, img, pt1, pt2, color, thickness=-1, r=12):
        """Menggambar persegi panjang dengan sudut melengkung (Rounded Rectangle)."""
        x1, y1 = pt1
        x2, y2 = pt2
        
        # Batasi radius agar tidak melebihi ukuran box
        w, h = abs(x2 - x1), abs(y2 - y1)
        r = min(r, w // 2, h // 2)
        
        if thickness == -1:
            # Filled rounded rect
            cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
            cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
            cv2.circle(img, (x1 + r, y1 + r), r, color, -1)
            cv2.circle(img, (x2 - r, y1 + r), r, color, -1)
            cv2.circle(img, (x1 + r, y2 - r), r, color, -1)
            cv2.circle(img, (x2 - r, y2 - r), r, color, -1)
        else:
            # Border rounded rect
            cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness)
            cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness)
            cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness)
            cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness)
            cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
            cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
            cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)
            cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)

    def draw_glass_panel(self, img, x, y, w, h, bg_color, alpha=0.65, border_color=None, r=12):
        """Menggambar panel Glassmorphic semi-transparan dengan border glow tipis."""
        overlay = img.copy()
        self.draw_rounded_rect(overlay, (x, y), (x + w, y + h), bg_color, -1, r=r)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        if border_color:
            self.draw_rounded_rect(img, (x, y), (x + w, y + h), border_color, 1, r=r)

    def draw_top_bar(self, frame, gesture, is_paused, keyboard_active, w_cam):
        """Menggambar Header Bar Minimalis di bagian atas layar kamera."""
        # Panel atas glassmorphic
        self.draw_glass_panel(frame, 15, 15, w_cam - 30, 55, self.COLOR_BG_DARK, alpha=0.75, border_color=self.COLOR_BORDER, r=14)
        
        # Logo & Judul Sistem
        cv2.putText(frame, "DACTYL-AI", (35, 49), self.font_bold, 0.75, self.COLOR_CYAN, 2, cv2.LINE_AA)
        cv2.putText(frame, "V2.5 MAGIC CURSOR", (165, 48), self.font, 0.45, self.COLOR_MUTED, 1, cv2.LINE_AA)
        
        # Indikator Status System (Kanan Atas)
        if is_paused:
            status_text = "SYSTEM LOCKED (PAUSED)"
            status_color = self.COLOR_CORAL
            dot_color = (0, 0, 255)
        elif keyboard_active:
            status_text = "HOLOGRAM KEYBOARD ACTIVE"
            status_color = self.COLOR_PURPLE
            dot_color = self.COLOR_PURPLE
        else:
            status_text = "SYSTEM ACTIVE & RUNNING"
            status_color = self.COLOR_EMERALD
            dot_color = self.COLOR_EMERALD
            
        # Draw Status Pill Badge di Kanan Atas
        text_size = cv2.getTextSize(status_text, self.font_bold, 0.5, 1)[0]
        pill_w = text_size[0] + 45
        pill_x = w_cam - 30 - pill_w - 5
        
        self.draw_rounded_rect(frame, (pill_x, 25), (pill_x + pill_w, 55), (20, 20, 20), -1, r=8)
        self.draw_rounded_rect(frame, (pill_x, 25), (pill_x + pill_w, 55), status_color, 1, r=8)
        cv2.circle(frame, (pill_x + 16, 40), 5, dot_color, -1)
        cv2.putText(frame, status_text, (pill_x + 32, 44), self.font_bold, 0.45, status_color, 1, cv2.LINE_AA)

    def draw_action_badge(self, frame, text, subtext="", color=(255, 212, 0), pos_y=85):
        """Menggambar Badge Aksi Minimalis (Pill Badge) saat ada interaksi/gestur aktif."""
        text_size = cv2.getTextSize(text, self.font_bold, 0.7, 2)[0]
        sub_size = cv2.getTextSize(subtext, self.font, 0.45, 1)[0] if subtext else (0, 0)
        
        box_w = max(text_size[0], sub_size[0]) + 40
        box_h = 60 if subtext else 45
        x = 25
        
        self.draw_glass_panel(frame, x, pos_y, box_w, box_h, self.COLOR_BG_DARK, alpha=0.85, border_color=color, r=10)
        
        # Aksen garis vertikal di sebelah kiri badge
        cv2.rectangle(frame, (x + 6, pos_y + 8), (x + 10, pos_y + box_h - 8), color, -1)
        
        cv2.putText(frame, text, (x + 22, pos_y + 30 if not subtext else pos_y + 27), self.font_bold, 0.65, self.COLOR_TEXT, 2, cv2.LINE_AA)
        if subtext:
            cv2.putText(frame, subtext, (x + 22, pos_y + 48), self.font, 0.42, color, 1, cv2.LINE_AA)

    def draw_locked_screen(self, frame, w_cam, h_cam):
        """Tampilan Overlay Khusus saat Sistem dalam Kondisi Locked/Standby (Label 7 / Paused)."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w_cam, h_cam), (10, 10, 25), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        
        # Glass Card Center
        card_w, card_h = 440, 140
        cx, cy = (w_cam - card_w) // 2, (h_cam - card_h) // 2
        self.draw_glass_panel(frame, cx, cy, card_w, card_h, (15, 15, 30), alpha=0.9, border_color=self.COLOR_CORAL, r=16)
        
        cv2.putText(frame, "SYSTEM LOCKED / STANDBY", (cx + 50, cy + 50), self.font_bold, 0.8, self.COLOR_CORAL, 2, cv2.LINE_AA)
        cv2.putText(frame, "Genggam tangan (Fist / Label 7) selama 1.0s", (cx + 45, cy + 85), self.font, 0.52, self.COLOR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(frame, "untuk membuka kunci (UNLOCK)", (cx + 105, cy + 112), self.font_bold, 0.5, self.COLOR_EMERALD, 1, cv2.LINE_AA)

    def draw_virtual_keyboard(self, frame, keyboard_keys, hover_start, current_hovered_keys, w_cam, h_cam):
        """Menggambar Hologram Virtual Keyboard bergaya Cyberpunk Modern Minimalis."""
        # Panel Background Keyboard di Bagian Bawah
        self.draw_glass_panel(frame, 80, 440, w_cam - 160, 265, self.COLOR_BG_DARK, alpha=0.82, border_color=self.COLOR_PURPLE, r=16)
        
        for k in keyboard_keys:
            key_name = k['key']
            x1, y1, x2, y2 = k['x1'], k['y1'], k['x2'], k['y2']
            
            is_hovered = key_name in current_hovered_keys
            
            # Tentukan Warna Tombol
            if is_hovered:
                bg_color = (60, 180, 255)  # Orange/Gold highlight
                text_color = (0, 0, 0)
                border_col = self.COLOR_CYAN
            else:
                bg_color = (40, 30, 25)    # Dark glass
                text_color = self.COLOR_TEXT
                border_col = (100, 90, 80)
                
            # Gambar Tombol
            self.draw_rounded_rect(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), bg_color, -1, r=8)
            self.draw_rounded_rect(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), border_col, 1 if not is_hovered else 2, r=8)
            
            # Posisi Teks agar di tengah tombol
            ts = cv2.getTextSize(key_name, self.font_bold, 0.55, 1)[0]
            tx = x1 + (x2 - x1 - ts[0]) // 2
            ty = y1 + (y2 - y1 + ts[1]) // 2
            cv2.putText(frame, key_name, (tx, ty - 2), self.font_bold, 0.55, text_color, 1, cv2.LINE_AA)
            
            # Jika sedang di-hover, gambarkan progress bar pengisian di bawah tombol
            if is_hovered and key_name in hover_start:
                elapsed = time.time() - hover_start[key_name]
                pct = min(elapsed / 1.0, 1.0)
                bar_w = int((x2 - x1 - 16) * pct)
                if bar_w > 0:
                    cv2.rectangle(frame, (x1 + 8, y2 - 12), (x1 + 8 + bar_w, y2 - 8), self.COLOR_EMERALD, -1)

    def draw_screenshot_viewfinder(self, frame, x1_cam, y1_cam, x2_cam, y2_cam, elapsed):
        """Menggambar Viewfinder Screenshot bergaya Neon Sci-Fi Minimalis."""
        # Overlay tint tipis di area yang dipilih
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1_cam, y1_cam), (x2_cam, y2_cam), (0, 180, 255), -1)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        
        # Sudut siku-siku futuristik
        size = 24
        thick = 3
        col = self.COLOR_CYAN
        
        cv2.line(frame, (x1_cam, y1_cam), (x1_cam + size, y1_cam), col, thick)
        cv2.line(frame, (x1_cam, y1_cam), (x1_cam, y1_cam + size), col, thick)
        cv2.line(frame, (x2_cam, y1_cam), (x2_cam - size, y1_cam), col, thick)
        cv2.line(frame, (x2_cam, y1_cam), (x2_cam, y1_cam + size), col, thick)
        cv2.line(frame, (x1_cam, y2_cam), (x1_cam + size, y2_cam), col, thick)
        cv2.line(frame, (x1_cam, y2_cam), (x1_cam, y2_cam - size), col, thick)
        cv2.line(frame, (x2_cam, y2_cam), (x2_cam - size, y2_cam), col, thick)
        cv2.line(frame, (x2_cam, y2_cam), (x2_cam, y2_cam - size), col, thick)
        
        # Progress Bar Countdown di atas kotak
        pct = min(elapsed / 1.5, 1.0)
        bar_w = int((x2_cam - x1_cam) * pct)
        if bar_w > 0:
            cv2.rectangle(frame, (x1_cam, y1_cam - 12), (x1_cam + bar_w, y1_cam - 6), self.COLOR_EMERALD, -1)
            
        cv2.putText(frame, f"CAPTURING AREA... {int(pct*100)}%", (x1_cam + 4, y1_cam - 18), self.font, 0.45, self.COLOR_CYAN, 1, cv2.LINE_AA)
