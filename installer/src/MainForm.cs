using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace YMBG
{
    internal sealed class MainForm : Form
    {
        private const int WindowW = 790;
        private const int WindowH = 650;

        [DllImport("user32.dll")]
        private static extern bool ReleaseCapture();

        [DllImport("user32.dll")]
        private static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);

        private readonly string startDirHint;
        private AppState state;
        private bool busy;
        private bool updateStarted;

        private IconTile logo;
        private IconTile heroIcon;
        private Label heroTitle;
        private Label heroSub;
        private Label appVersion;
        private Label appPath;
        private Label patchState;
        private Label patchHint;
        private Label engineState;
        private Label engineHint;
        private Label versionText;
        private Dot patchDot;
        private Dot engineDot;
        private RoundButton installBtn;
        private RoundButton uninstallBtn;
        private RoundButton folderBtn;
        private RoundButton launchBtn;
        private RoundButton minBtn;
        private RoundButton closeBtn;
        private YmCheck launchAfter;
        private YmCheck removeSettings;
        private ProgressStrip progress;
        private TextBox logBox;

        public MainForm(string appDirHint)
        {
            startDirHint = appDirHint;

            Text = "Фон Яндекс Музыки — установщик";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(WindowW, WindowH);
            BackColor = Ui.Bg;
            Font = Ui.Body;
            DoubleBuffered = true;
            KeyPreview = true;
            AutoScaleMode = AutoScaleMode.Dpi;
            AutoScaleDimensions = new SizeF(96f, 96f);

            BuildLayout();
            WireEvents();
        }

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            AppendLog("Установщик готов.");
            RefreshState();
            CheckForUpdates();
        }

        protected override void OnResize(EventArgs e)
        {
            base.OnResize(e);
            if (WindowState == FormWindowState.Minimized)
            {
                return;
            }
            using (GraphicsPath path = Ui.Round(new Rectangle(0, 0, Width, Height), 18))
            {
                Region = new Region(path);
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (GraphicsPath path = Ui.Round(new Rectangle(0, 0, Width - 1, Height - 1), 18))
            using (Pen pen = new Pen(Ui.Border, 1f))
            {
                e.Graphics.DrawPath(pen, path);
            }
        }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            base.OnKeyDown(e);
            if (e.KeyCode == Keys.Escape && !busy)
            {
                Close();
            }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (busy)
            {
                e.Cancel = true;
                MessageBox.Show(this, "Дождитесь окончания операции.", "Установщик",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            base.OnFormClosing(e);
        }

        private void BuildLayout()
        {
            SuspendLayout();

            // --- заголовок ---------------------------------------------------
            logo = new IconTile();
            logo.Bounds = new Rectangle(22, 14, 30, 30);
            logo.Glyph = "♪";
            logo.Fill = Ui.Accent;
            logo.GlyphColor = Ui.Ink;
            logo.Radius = 9;
            logo.Font = Ui.LogoGlyph;
            logo.BackColor = Ui.Bg;
            Controls.Add(logo);

            Label title = Ui.MakeLabel("Фон Яндекс Музыки", Ui.Title, Ui.TextMain, Ui.Bg);
            title.Bounds = new Rectangle(64, 8, 380, 22);
            Controls.Add(title);

            Label subtitle = Ui.MakeLabel("установщик", Ui.Subtitle, Ui.TextMuted, Ui.Bg);
            subtitle.Bounds = new Rectangle(64, 29, 300, 15);
            Controls.Add(subtitle);

            minBtn = new RoundButton();
            minBtn.Bounds = new Rectangle(698, 14, 38, 30);
            minBtn.Text = "—";
            minBtn.Font = new Font("Segoe UI", 11.25f);
            minBtn.Radius = 8;
            minBtn.Fill = Ui.Bg;
            minBtn.Hover = Color.FromArgb(0x26, 0x26, 0x2B);
            minBtn.TextColor = Color.FromArgb(0xA0, 0xA0, 0xA8);
            minBtn.BorderColor = Color.Empty;
            Controls.Add(minBtn);

            closeBtn = new RoundButton();
            closeBtn.Bounds = new Rectangle(740, 14, 38, 30);
            closeBtn.Text = "✕";
            closeBtn.Font = new Font("Segoe UI", 10.5f);
            closeBtn.Radius = 8;
            closeBtn.Fill = Ui.Bg;
            closeBtn.Hover = Color.FromArgb(0x2A, 0x1A, 0x1D);
            closeBtn.TextColor = Color.FromArgb(0xA0, 0xA0, 0xA8);
            closeBtn.BorderColor = Color.Empty;
            Controls.Add(closeBtn);

            // --- большая карточка статуса ------------------------------------
            CardPanel hero = new CardPanel();
            hero.Bounds = new Rectangle(24, 66, 742, 92);
            hero.Fill = Ui.CardHero;
            hero.Radius = 14;
            Controls.Add(hero);

            heroIcon = new IconTile();
            heroIcon.Bounds = new Rectangle(42, 85, 54, 54);
            heroIcon.Glyph = "…";
            heroIcon.Fill = Color.FromArgb(0x20, 0x20, 0x2A);
            heroIcon.GlyphColor = Ui.TextMuted;
            heroIcon.Radius = 16;
            heroIcon.Font = Ui.HeroGlyph;
            heroIcon.BackColor = Ui.CardHero;
            Controls.Add(heroIcon);

            heroTitle = Ui.MakeLabel("Проверяю…", Ui.Hero, Ui.TextMain, Ui.CardHero);
            heroTitle.Bounds = new Rectangle(114, 82, 620, 28);
            Controls.Add(heroTitle);

            heroSub = Ui.MakeLabel("Смотрю, что установлено в системе.", Ui.HeroSub, Ui.TextMuted, Ui.CardHero);
            heroSub.Bounds = new Rectangle(114, 113, 620, 36);
            Controls.Add(heroSub);

            // --- карточка с деталями -----------------------------------------
            CardPanel info = new CardPanel();
            info.Bounds = new Rectangle(24, 170, 742, 96);
            info.Fill = Ui.Card;
            info.Radius = 14;
            Controls.Add(info);

            Label l1 = Ui.MakeLabel("ЯНДЕКС МУЗЫКА", Ui.Caption, Ui.TextFaint, Ui.Card);
            l1.Bounds = new Rectangle(42, 184, 300, 15);
            Controls.Add(l1);

            appVersion = Ui.MakeLabel("—", Ui.Value, Ui.TextMain, Ui.Card);
            appVersion.Bounds = new Rectangle(42, 202, 300, 22);
            Controls.Add(appVersion);

            appPath = Ui.MakeLabel("—", Ui.Hint, Ui.TextFaint, Ui.Card);
            appPath.Bounds = new Rectangle(42, 228, 310, 16);
            appPath.AutoEllipsis = true;
            Controls.Add(appPath);

            Label l2 = Ui.MakeLabel("ПАТЧ", Ui.Caption, Ui.TextFaint, Ui.Card);
            l2.Bounds = new Rectangle(366, 184, 180, 15);
            Controls.Add(l2);

            patchDot = new Dot();
            patchDot.Bounds = new Rectangle(366, 208, 8, 8);
            patchDot.BackColor = Ui.Card;
            Controls.Add(patchDot);

            patchState = Ui.MakeLabel("Проверяю…", Ui.Body, Ui.TextMain, Ui.Card);
            patchState.Bounds = new Rectangle(380, 201, 160, 22);
            Controls.Add(patchState);

            patchHint = Ui.MakeLabel("", Ui.Hint, Ui.TextFaint, Ui.Card);
            patchHint.Bounds = new Rectangle(366, 228, 175, 16);
            Controls.Add(patchHint);

            Label l3 = Ui.MakeLabel("ДВИЖОК", Ui.Caption, Ui.TextFaint, Ui.Card);
            l3.Bounds = new Rectangle(559, 184, 170, 15);
            Controls.Add(l3);

            engineDot = new Dot();
            engineDot.Bounds = new Rectangle(559, 208, 8, 8);
            engineDot.BackColor = Ui.Card;
            Controls.Add(engineDot);

            engineState = Ui.MakeLabel("Встроен", Ui.Body, Ui.TextMain, Ui.Card);
            engineState.Bounds = new Rectangle(573, 201, 150, 22);
            Controls.Add(engineState);

            engineHint = Ui.MakeLabel("Python не нужен", Ui.Hint, Ui.TextFaint, Ui.Card);
            engineHint.Bounds = new Rectangle(559, 228, 183, 16);
            Controls.Add(engineHint);

            // --- кнопки ------------------------------------------------------
            installBtn = new RoundButton();
            installBtn.Bounds = new Rectangle(24, 282, 190, 44);
            installBtn.Text = "Установить";
            installBtn.Font = Ui.Button;
            installBtn.Radius = 11;
            installBtn.Fill = Ui.Accent;
            installBtn.Hover = Ui.AccentHover;
            installBtn.TextColor = Ui.Ink;
            installBtn.BorderColor = Color.Empty;
            installBtn.FillDisabled = Ui.DisabledFill;
            installBtn.TextDisabled = Ui.DisabledText;
            Controls.Add(installBtn);

            uninstallBtn = new RoundButton();
            uninstallBtn.Bounds = new Rectangle(224, 282, 120, 44);
            uninstallBtn.Text = "Удалить";
            uninstallBtn.Font = Ui.ButtonSmall;
            uninstallBtn.Radius = 10;
            uninstallBtn.Fill = Ui.Danger;
            uninstallBtn.Hover = Ui.DangerHover;
            uninstallBtn.BorderColor = Ui.DangerBorder;
            uninstallBtn.TextColor = Ui.DangerText;
            uninstallBtn.BorderDisabled = Color.FromArgb(0x2A, 0x20, 0x22);
            Controls.Add(uninstallBtn);

            folderBtn = new RoundButton();
            folderBtn.Bounds = new Rectangle(450, 284, 152, 40);
            folderBtn.Text = "Папка с фонами";
            folderBtn.Font = Ui.ButtonSmall;
            folderBtn.Radius = 10;
            folderBtn.Fill = Ui.Ghost;
            folderBtn.Hover = Ui.GhostHover;
            folderBtn.BorderColor = Ui.GhostBorder;
            folderBtn.TextColor = Ui.TextSoft;
            Controls.Add(folderBtn);

            launchBtn = new RoundButton();
            launchBtn.Bounds = new Rectangle(610, 284, 156, 40);
            launchBtn.Text = "Запустить Музыку";
            launchBtn.Font = Ui.ButtonSmall;
            launchBtn.Radius = 10;
            launchBtn.Fill = Ui.Ghost;
            launchBtn.Hover = Ui.GhostHover;
            launchBtn.BorderColor = Ui.GhostBorder;
            launchBtn.TextColor = Ui.TextSoft;
            Controls.Add(launchBtn);

            // --- галочки -----------------------------------------------------
            launchAfter = new YmCheck();
            launchAfter.Bounds = new Rectangle(26, 340, 420, 20);
            launchAfter.Text = "Запустить Яндекс Музыку после установки";
            launchAfter.Checked = true;
            Controls.Add(launchAfter);

            removeSettings = new YmCheck();
            removeSettings.Bounds = new Rectangle(26, 366, 520, 20);
            removeSettings.Text = "При удалении также стереть настройки и фоны";
            removeSettings.Checked = false;
            Controls.Add(removeSettings);

            // --- прогресс и журнал -------------------------------------------
            progress = new ProgressStrip();
            progress.Bounds = new Rectangle(24, 394, 742, 3);
            Controls.Add(progress);

            CardPanel logCard = new CardPanel();
            logCard.Bounds = new Rectangle(24, 408, 742, 164);
            logCard.Fill = Ui.Card;
            logCard.Radius = 14;
            Controls.Add(logCard);

            logBox = new TextBox();
            logBox.Bounds = new Rectangle(32, 416, 726, 148);
            logBox.BackColor = Ui.CardDeep;
            logBox.ForeColor = Ui.TextMuted;
            logBox.BorderStyle = BorderStyle.None;
            logBox.Font = Ui.Mono;
            logBox.Multiline = true;
            logBox.ReadOnly = true;
            logBox.ScrollBars = ScrollBars.None;
            logBox.WordWrap = true;
            logBox.TabStop = false;
            Controls.Add(logBox);

            // --- подвал ------------------------------------------------------
            Label disclaimer = Ui.MakeLabel("Неофициальный мод · не связан с Яндексом · используйте на свой риск",
                Ui.Footer, Color.FromArgb(0x60, 0x60, 0x69), Ui.Bg);
            disclaimer.Bounds = new Rectangle(24, 606, 560, 18);
            Controls.Add(disclaimer);

            versionText = Ui.MakeLabel("v" + Core.InstallerVersion, Ui.Footer,
                Color.FromArgb(0x60, 0x60, 0x69), Ui.Bg);
            versionText.Bounds = new Rectangle(590, 606, 176, 18);
            versionText.TextAlign = ContentAlignment.MiddleRight;
            Controls.Add(versionText);

            // перетаскивание окна за заголовок
            MouseEventHandler drag = DragWindow;
            logo.MouseDown += drag;
            title.MouseDown += drag;
            subtitle.MouseDown += drag;
            MouseDown += drag;

            // Карточки добавлены раньше и иначе оказываются поверх подписей:
            // в WinForms первый добавленный контрол — самый верхний.
            hero.SendToBack();
            info.SendToBack();
            logCard.SendToBack();

            ResumeLayout(false);
        }

        private void WireEvents()
        {
            closeBtn.Click += delegate
            {
                if (busy)
                {
                    MessageBox.Show(this, "Дождитесь окончания операции.", "Установщик",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return;
                }
                Close();
            };
            minBtn.Click += delegate { WindowState = FormWindowState.Minimized; };
            installBtn.Click += delegate { RunOperation(true); };
            uninstallBtn.Click += delegate { RunOperation(false); };
            folderBtn.Click += delegate { OpenBackgroundsFolder(); };
            launchBtn.Click += delegate { StartMusic(); };
        }

        private void DragWindow(object sender, MouseEventArgs e)
        {
            if (e.Button != MouseButtons.Left)
            {
                return;
            }
            ReleaseCapture();
            SendMessage(Handle, 0xA1, (IntPtr)2, IntPtr.Zero);
        }

        private void SetHero(string glyph, Color glyphColor, string title, string subtitle)
        {
            heroIcon.Glyph = glyph;
            heroIcon.GlyphColor = glyphColor;
            heroIcon.Invalidate();
            heroTitle.Text = title;
            heroSub.Text = subtitle;
        }

        private void AppendLog(string message)
        {
            if (string.IsNullOrEmpty(message))
            {
                return;
            }
            string stamp = DateTime.Now.ToString("HH:mm:ss");
            string text = message.Replace("\r\n", "\n").Replace('\r', '\n');
            string[] lines = text.Split('\n');
            for (int i = 0; i < lines.Length; i++)
            {
                string line = lines[i].TrimEnd();
                if (line.Length == 0)
                {
                    continue;
                }
                logBox.AppendText("[" + stamp + "] " + line + "\r\n");
            }
            logBox.SelectionStart = logBox.TextLength;
            logBox.ScrollToCaret();
        }

        private void Post(Action action)
        {
            if (IsDisposed)
            {
                return;
            }
            try
            {
                BeginInvoke(action);
            }
            catch (ObjectDisposedException)
            {
            }
            catch (InvalidOperationException)
            {
            }
        }

        private void RefreshState()
        {
            if (busy)
            {
                return;
            }
            installBtn.Enabled = false;
            uninstallBtn.Enabled = false;
            launchBtn.Enabled = false;

            string hint = startDirHint;
            Task<AppState> task = Task.Factory.StartNew<AppState>(delegate
            {
                return Core.GetState(hint);
            });
            task.ContinueWith(delegate(Task<AppState> t)
            {
                Post(delegate
                {
                    if (t.IsFaulted)
                    {
                        Exception ex = t.Exception == null ? null : t.Exception.GetBaseException();
                        AppendLog("Не удалось проверить состояние: " + (ex == null ? "неизвестная ошибка" : ex.Message));
                        return;
                    }
                    ApplyState(t.Result);
                });
            });
        }

        private void ApplyState(AppState s)
        {
            state = s;

            if (!s.Found)
            {
                appVersion.Text = "—";
                appPath.Text = "не найдена";
                patchDot.FillColor = Ui.Red;
                patchDot.Invalidate();
                patchState.Text = "—";
                patchHint.Text = "Клиент не найден";
                engineDot.FillColor = Ui.Green;
                engineDot.Invalidate();
                engineState.Text = "Встроен";
                engineHint.Text = "Python не нужен";
                SetHero("!", Ui.Red, "Яндекс Музыка не найдена",
                    "Установите клиент Яндекс Музыки, затем запустите установщик снова.");
                installBtn.Text = "Установить";
                UpdateButtons();
                return;
            }

            appVersion.Text = string.IsNullOrEmpty(s.Version) ? "версия неизвестна" : s.Version;
            appPath.Text = s.Dir;

            if (s.Error != null)
            {
                patchDot.FillColor = Ui.Red;
                patchState.Text = "Ошибка";
                patchHint.Text = "app.asar не читается";
            }
            else if (s.PatchCurrent)
            {
                patchDot.FillColor = Ui.Green;
                patchState.Text = "Установлен";
                patchHint.Text = "Вкладка «Фон» доступна";
            }
            else if (s.PatchPresent)
            {
                patchDot.FillColor = Ui.YellowDot;
                patchState.Text = "Устарел";
                patchHint.Text = "Нужно перепатчить";
            }
            else
            {
                patchDot.FillColor = Ui.Red;
                patchState.Text = "Не установлен";
                patchHint.Text = s.HasAsarBackup ? "Есть бэкап оригинала" : "Нажмите «Установить»";
            }
            patchDot.Invalidate();

            engineDot.FillColor = Ui.Green;
            engineDot.Invalidate();
            engineState.Text = "Встроен";
            engineHint.Text = "Python не нужен";

            if (s.Error != null)
            {
                SetHero("!", Ui.Red, "Клиент не читается", s.Error);
                installBtn.Text = "Установить";
            }
            else if (s.PatchCurrent)
            {
                string subtitle = "Фон и вкладка «Фон» уже внутри Яндекс Музыки.";
                if (s.FuseState == Fuse.State.Enabled)
                {
                    subtitle += " Но проверка целостности включена — нажмите «Переустановить».";
                }
                SetHero("✓", Ui.Green, "Всё готово", subtitle);
                installBtn.Text = "Переустановить";
            }
            else if (s.PatchPresent)
            {
                SetHero("↑", Ui.YellowDot, "Патч устарел",
                    "Код мода обновился — нажмите «Переустановить».");
                installBtn.Text = "Переустановить";
            }
            else
            {
                SetHero("↓", Ui.Accent, "Готово к установке",
                    "Установщик добавит фон и вкладку «Фон» в Яндекс Музыку.");
                installBtn.Text = "Установить";
            }

            UpdateButtons();
        }

        private void UpdateButtons()
        {
            bool ok = state != null && state.Found;
            installBtn.Enabled = !busy && ok;
            uninstallBtn.Enabled = !busy && ok &&
                (state.PatchPresent || state.HasAsarBackup || state.HasExeBackup);
            folderBtn.Enabled = !busy;
            launchBtn.Enabled = !busy && ok && !string.IsNullOrEmpty(state.Exe);
        }

        private void SetBusy(bool value)
        {
            busy = value;
            progress.Active = value;
            installBtn.Enabled = !value;
            uninstallBtn.Enabled = !value;
            folderBtn.Enabled = !value;
            launchBtn.Enabled = !value;
            launchAfter.Enabled = !value;
            removeSettings.Enabled = !value;
            minBtn.Enabled = !value;
            closeBtn.Enabled = true;
        }

        private void RunOperation(bool install)
        {
            if (busy || state == null || !state.Found)
            {
                return;
            }
            if (!install)
            {
                DialogResult answer = MessageBox.Show(this,
                    "Вернуть оригинальные файлы Яндекс Музыки?\n\nПатч будет удалён, фон и вкладка «Фон» исчезнут.",
                    "Удаление", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (answer != DialogResult.Yes)
                {
                    return;
                }
            }

            SetBusy(true);
            SetHero("…", Ui.Accent, install ? "Установка…" : "Удаление…",
                "Не закрывайте окно, это займёт несколько секунд.");
            AppendLog(install ? "Ставлю патч…" : "Удаляю патч…");

            string hint = startDirHint;
            Action<string> log = delegate(string message)
            {
                Post(delegate { AppendLog(message); });
            };

            Task<Exception> task = Task.Factory.StartNew<Exception>(delegate
            {
                try
                {
                    if (install)
                    {
                        Core.Apply(hint, false, log);
                    }
                    else
                    {
                        Core.Restore(hint, false, log);
                    }
                    return null;
                }
                catch (Exception ex)
                {
                    return ex;
                }
            });
            task.ContinueWith(delegate(Task<Exception> t)
            {
                Post(delegate { FinishOperation(install, t.Result); });
            });
        }

        private void FinishOperation(bool install, Exception error)
        {
            if (error != null)
            {
                AppendLog("Ошибка: " + error.Message);
                MessageBox.Show(this, error.Message, "Не получилось",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            else
            {
                if (install)
                {
                    if (launchAfter.Checked && state != null && !string.IsNullOrEmpty(state.Exe))
                    {
                        try
                        {
                            Core.StartApp(state.Exe, AppendLog);
                        }
                        catch (Exception ex)
                        {
                            AppendLog("Не удалось запустить Музыку: " + ex.Message);
                        }
                    }
                }
                else if (removeSettings.Checked)
                {
                    Core.DeleteSettings();
                    AppendLog("Настройки и фоны удалены.");
                }
            }
            busy = false;
            progress.Active = false;
            RefreshState();
        }

        /// <summary>
        /// Тихо проверяет GitHub Releases. Если вышла новая версия — сама
        /// скачивает её и предлагает перезапуститься. Ручная загрузка не нужна.
        /// </summary>
        private void CheckForUpdates()
        {
            if (updateStarted)
            {
                return;
            }
            updateStarted = true;

            Task<UpdateInfo> task = Task.Factory.StartNew<UpdateInfo>(delegate
            {
                return Updater.Check();
            });
            task.ContinueWith(delegate(Task<UpdateInfo> t)
            {
                if (t.IsFaulted)
                {
                    Exception ex = t.Exception == null ? null : t.Exception.GetBaseException();
                    Post(delegate
                    {
                        AppendLog("Обновления: " + (ex == null ? "неизвестная ошибка" : ex.Message));
                    });
                    return;
                }
                UpdateInfo info = t.Result;
                Post(delegate { OnUpdateChecked(info); });
            });
        }

        private void OnUpdateChecked(UpdateInfo info)
        {
            if (info == null)
            {
                return;
            }
            if (info.Error != null)
            {
                AppendLog("Обновления: " + info.Error);
                return;
            }
            if (!info.Available)
            {
                AppendLog("Установщик " + Core.InstallerVersion + " — последняя версия.");
                return;
            }

            AppendLog("Доступно обновление " + info.Version + ".");
            SetHero("↑", Ui.Accent, "Есть обновление " + info.Version,
                "Скачиваю новую версию установщика — вручную ничего качать не нужно.");
            DownloadUpdate(info);
        }

        private void DownloadUpdate(UpdateInfo info)
        {
            Task<string> task = Task.Factory.StartNew<string>(delegate
            {
                return Updater.Download(info, delegate(string message)
                {
                    Post(delegate { AppendLog(message); });
                });
            });
            task.ContinueWith(delegate(Task<string> t)
            {
                Post(delegate { OnUpdateDownloaded(info, t); });
            });
        }

        private void OnUpdateDownloaded(UpdateInfo info, Task<string> task)
        {
            if (task.IsFaulted)
            {
                Exception ex = task.Exception == null ? null : task.Exception.GetBaseException();
                AppendLog("Обновление не скачалось: " + (ex == null ? "неизвестная ошибка" : ex.Message));
                RefreshState();
                return;
            }

            SetHero("↑", Ui.Accent, "Обновление " + info.Version + " готово",
                "Перезапущу установщик, чтобы применить новую версию.");
            AppendLog("Обновление " + info.Version + " скачано.");

            if (busy)
            {
                AppendLog("Завершите текущую операцию и запустите установщик снова — обновление применится тогда.");
                return;
            }

            DialogResult answer = MessageBox.Show(this,
                "Вышла версия " + info.Version + ".\n\n" +
                "Перезапустить установщик и обновить его сейчас?\n" +
                "Настройки и фоны останутся на месте.",
                "Обновление установщика", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (answer != DialogResult.Yes)
            {
                AppendLog("Обновление отложено. Файл сохранён, при следующем запуске качать заново не придётся.");
                RefreshState();
                return;
            }

            try
            {
                SetBusy(true);
                Updater.Apply(task.Result, AppendLog);
            }
            catch (Exception ex)
            {
                busy = false;
                progress.Active = false;
                AppendLog("Не удалось обновить установщик: " + ex.Message);
                MessageBox.Show(this, ex.Message, "Обновление", MessageBoxButtons.OK, MessageBoxIcon.Error);
                RefreshState();
                return;
            }
            // Новый процесс уже запущен и ждёт, пока этот отпустит мьютекс.
            Environment.Exit(0);
        }

        private void OpenBackgroundsFolder()
        {
            string dir = Core.UserDir;
            if (!Directory.Exists(dir))
            {
                MessageBox.Show(this, "Папка ещё не создана. Сначала установите патч.", "Фон",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            try
            {
                Process.Start("explorer.exe", "\"" + dir + "\"");
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "Не удалось открыть папку",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void StartMusic()
        {
            if (state == null || string.IsNullOrEmpty(state.Exe))
            {
                return;
            }
            try
            {
                Core.StartApp(state.Exe, AppendLog);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "Не удалось запустить Музыку",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
