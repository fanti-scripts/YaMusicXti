using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;

namespace YMBG
{
    /// <summary>Тёмная тема: цвета, шрифты и мелкие рисованные контролы.</summary>
    internal static class Ui
    {
        public static readonly Color Bg = Color.FromArgb(0x10, 0x10, 0x12);
        public static readonly Color Card = Color.FromArgb(0x17, 0x17, 0x1A);
        public static readonly Color CardHero = Color.FromArgb(0x15, 0x15, 0x18);
        public static readonly Color CardDeep = Color.FromArgb(0x0D, 0x0D, 0x0F);
        public static readonly Color Border = Color.FromArgb(0x26, 0x26, 0x2B);
        public static readonly Color TextMain = Color.FromArgb(0xF1, 0xF1, 0xF4);
        public static readonly Color TextSoft = Color.FromArgb(0xC9, 0xC9, 0xCF);
        public static readonly Color TextMuted = Color.FromArgb(0x8F, 0x8F, 0x98);
        public static readonly Color TextFaint = Color.FromArgb(0x6F, 0x6F, 0x78);
        public static readonly Color Accent = Color.FromArgb(0xFF, 0xCC, 0x00);
        public static readonly Color AccentHover = Color.FromArgb(0xFF, 0xD6, 0x33);
        public static readonly Color Ink = Color.FromArgb(0x14, 0x14, 0x14);
        public static readonly Color Green = Color.FromArgb(0x5F, 0xD1, 0x6B);
        public static readonly Color Red = Color.FromArgb(0xE0, 0x6C, 0x6C);
        public static readonly Color Ghost = Color.FromArgb(0x1B, 0x1B, 0x1F);
        public static readonly Color GhostHover = Color.FromArgb(0x24, 0x24, 0x2A);
        public static readonly Color GhostBorder = Color.FromArgb(0x2C, 0x2C, 0x32);
        public static readonly Color Danger = Color.FromArgb(0x24, 0x14, 0x17);
        public static readonly Color DangerHover = Color.FromArgb(0x34, 0x1B, 0x1F);
        public static readonly Color DangerBorder = Color.FromArgb(0x4A, 0x25, 0x2A);
        public static readonly Color DangerText = Color.FromArgb(0xFF, 0x8D, 0x8D);
        public static readonly Color DisabledFill = Color.FromArgb(0x33, 0x33, 0x38);
        public static readonly Color DisabledText = Color.FromArgb(0x77, 0x77, 0x7F);
        public static readonly Color YellowDot = Color.FromArgb(0xE8, 0xB9, 0x00);

        public static readonly Font Body = new Font("Segoe UI", 9.5f);
        public static readonly Font Title = new Font("Segoe UI", 11.25f, FontStyle.Bold);
        public static readonly Font Subtitle = new Font("Segoe UI", 8.5f);
        public static readonly Font Hero = new Font("Segoe UI", 14.25f, FontStyle.Bold);
        public static readonly Font HeroSub = new Font("Segoe UI", 9.5f);
        public static readonly Font HeroGlyph = new Font("Segoe UI", 21f, FontStyle.Bold);
        public static readonly Font LogoGlyph = new Font("Segoe UI", 13f, FontStyle.Bold);
        public static readonly Font Caption = new Font("Segoe UI", 8f, FontStyle.Bold);
        public static readonly Font Value = new Font("Segoe UI", 12f, FontStyle.Bold);
        public static readonly Font Hint = new Font("Segoe UI", 8.25f);
        public static readonly Font Button = new Font("Segoe UI", 10.5f, FontStyle.Bold);
        public static readonly Font ButtonSmall = new Font("Segoe UI", 9.75f);
        public static readonly Font Check = new Font("Segoe UI", 9.4f);
        public static readonly Font Footer = new Font("Segoe UI", 8f);
        public static readonly Font Mono = new Font("Consolas", 8.5f);

        public static GraphicsPath Round(Rectangle rect, int radius)
        {
            GraphicsPath path = new GraphicsPath();
            int d = Math.Max(0, Math.Min(radius * 2, Math.Min(rect.Width, rect.Height)));
            if (d <= 1)
            {
                path.AddRectangle(rect);
                return path;
            }
            path.AddArc(rect.Left, rect.Top, d, d, 180, 90);
            path.AddArc(rect.Right - d, rect.Top, d, d, 270, 90);
            path.AddArc(rect.Right - d, rect.Bottom - d, d, d, 0, 90);
            path.AddArc(rect.Left, rect.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        public static void Text(Graphics g, string text, Font font, Color color, Rectangle bounds, TextFormatFlags flags)
        {
            TextRenderer.DrawText(g, text, font, bounds, color,
                flags | TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix);
        }

        public static Label MakeLabel(string text, Font font, Color color, Color back)
        {
            Label label = new Label();
            label.Text = text;
            label.Font = font;
            label.ForeColor = color;
            label.BackColor = back;
            label.AutoSize = false;
            label.TextAlign = ContentAlignment.MiddleLeft;
            return label;
        }
    }

    internal class CardPanel : Panel
    {
        public int Radius = 14;
        public Color Fill = Ui.Card;
        public Color BorderColor = Ui.Border;

        public CardPanel()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw |
                     ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Ui.Bg;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.Clear(BackColor);
            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = Ui.Round(r, Radius))
            using (SolidBrush brush = new SolidBrush(Fill))
            using (Pen pen = new Pen(BorderColor, 1f))
            {
                e.Graphics.FillPath(brush, path);
                e.Graphics.DrawPath(pen, path);
            }
            base.OnPaint(e);
        }
    }

    internal class RoundButton : Button
    {
        public int Radius = 10;
        public Color Fill = Ui.Ghost;
        public Color Hover = Ui.GhostHover;
        public Color BorderColor = Ui.GhostBorder;
        public Color TextColor = Ui.TextSoft;
        public Color FillDisabled = Ui.DisabledFill;
        public Color TextDisabled = Ui.DisabledText;
        public Color BorderDisabled = Color.Empty;

        public RoundButton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            UseVisualStyleBackColor = false;
            BackColor = Ui.Bg;
            Cursor = Cursors.Hand;
            TabStop = false;
            Font = Ui.ButtonSmall;
            ForeColor = Ui.TextSoft;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.Clear(BackColor);
            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            bool over = Enabled && ClientRectangle.Contains(PointToClient(Cursor.Position));
            using (GraphicsPath path = Ui.Round(r, Radius))
            {
                Color fill = Enabled ? (over ? Hover : Fill) : FillDisabled;
                using (SolidBrush brush = new SolidBrush(fill))
                {
                    e.Graphics.FillPath(brush, path);
                }
                Color border = Enabled ? BorderColor : BorderDisabled;
                if (border != Color.Empty)
                {
                    using (Pen pen = new Pen(border, 1f))
                    {
                        e.Graphics.DrawPath(pen, path);
                    }
                }
            }
            Ui.Text(e.Graphics, Text, Font, Enabled ? TextColor : TextDisabled, ClientRectangle,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
            if (Focused && ShowFocusCues)
            {
                // фокус не рисуем: кнопки не входят в Tab-порядок
            }
        }

        protected override void OnMouseEnter(EventArgs e)
        {
            base.OnMouseEnter(e);
            Invalidate();
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            base.OnMouseLeave(e);
            Invalidate();
        }

        protected override void OnEnabledChanged(EventArgs e)
        {
            base.OnEnabledChanged(e);
            Cursor = Enabled ? Cursors.Hand : Cursors.Default;
            Invalidate();
        }
    }

    internal class YmCheck : CheckBox
    {
        public YmCheck()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Ui.Bg;
            ForeColor = Ui.TextSoft;
            Font = Ui.Check;
            Cursor = Cursors.Hand;
            AutoSize = false;
            Height = 20;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.Clear(BackColor);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            int box = 18;
            int top = (Height - box) / 2;
            Rectangle r = new Rectangle(0, top, box - 1, box - 1);
            bool on = Checked;
            using (GraphicsPath path = Ui.Round(r, 5))
            {
                using (SolidBrush brush = new SolidBrush(on ? Ui.Accent : Color.FromArgb(0x1B, 0x1B, 0x1F)))
                {
                    e.Graphics.FillPath(brush, path);
                }
                using (Pen pen = new Pen(on ? Ui.Accent : Color.FromArgb(0x3A, 0x3A, 0x40), 1.4f))
                {
                    e.Graphics.DrawPath(pen, path);
                }
            }
            if (on)
            {
                using (Pen pen = new Pen(Ui.Ink, 2f))
                {
                    pen.StartCap = LineCap.Round;
                    pen.EndCap = LineCap.Round;
                    e.Graphics.DrawLines(pen, new Point[]
                    {
                        new Point(4, top + 9),
                        new Point(7, top + 12),
                        new Point(13, top + 5)
                    });
                }
            }
            Rectangle text = new Rectangle(box + 9, 0, Math.Max(0, Width - box - 9), Height);
            Ui.Text(e.Graphics, Text, Font, Enabled ? ForeColor : Ui.TextFaint, text,
                TextFormatFlags.Left | TextFormatFlags.VerticalCenter);
        }
    }

    internal class Dot : Control
    {
        public Color FillColor = Ui.TextMuted;

        public Dot()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            Size = new Size(8, 8);
            BackColor = Ui.Card;
            TabStop = false;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.Clear(BackColor);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (SolidBrush brush = new SolidBrush(FillColor))
            {
                e.Graphics.FillEllipse(brush, 0, 0, Width - 1, Height - 1);
            }
        }
    }

    internal class IconTile : Control
    {
        public string Glyph = "♪";
        public Color GlyphColor = Ui.Ink;
        public Color Fill = Ui.Accent;
        public int Radius = 9;

        public IconTile()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Ui.Bg;
            TabStop = false;
            Font = Ui.LogoGlyph;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.Clear(BackColor);
            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = Ui.Round(r, Radius))
            using (SolidBrush brush = new SolidBrush(Fill))
            {
                e.Graphics.FillPath(brush, path);
            }
            using (StringFormat sf = new StringFormat())
            {
                sf.Alignment = StringAlignment.Center;
                sf.LineAlignment = StringAlignment.Center;
                using (SolidBrush brush = new SolidBrush(GlyphColor))
                {
                    e.Graphics.DrawString(Glyph, Font, brush, new RectangleF(0, 0, Width, Height + 1), sf);
                }
            }
        }
    }

    internal class ProgressStrip : Control
    {
        private readonly Timer timer;
        private int position;
        private bool active;

        public ProgressStrip()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            Height = 3;
            BackColor = Ui.Bg;
            TabStop = false;
            timer = new Timer();
            timer.Interval = 16;
            timer.Tick += delegate
            {
                int span = Math.Max(1, Width);
                position += Math.Max(4, span / 70);
                if (position > span)
                {
                    position = -Math.Max(60, span / 4);
                }
                Invalidate();
            };
        }

        public bool Active
        {
            get { return active; }
            set
            {
                if (active == value)
                {
                    return;
                }
                active = value;
                if (active)
                {
                    position = -Math.Max(60, Width / 4);
                    timer.Start();
                }
                else
                {
                    timer.Stop();
                }
                Invalidate();
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.Clear(BackColor);
            using (SolidBrush back = new SolidBrush(Color.FromArgb(0x2A, 0x2A, 0x2E)))
            {
                e.Graphics.FillRectangle(back, 0, 0, Width, Height);
            }
            if (!active)
            {
                return;
            }
            int barWidth = Math.Max(60, Width / 4);
            Rectangle bar = new Rectangle(position, 0, barWidth, Height);
            using (LinearGradientBrush brush = new LinearGradientBrush(
                new Rectangle(bar.X - 1, 0, bar.Width + 2, Math.Max(1, Height)),
                Color.FromArgb(0, 0xFF, 0xCC, 0x00),
                Color.FromArgb(255, 0xFF, 0xCC, 0x00),
                LinearGradientMode.Horizontal))
            {
                ColorBlend blend = new ColorBlend();
                blend.Colors = new Color[]
                {
                    Color.FromArgb(0, 0xFF, 0xCC, 0x00),
                    Color.FromArgb(255, 0xFF, 0xCC, 0x00),
                    Color.FromArgb(255, 0xFF, 0xCC, 0x00),
                    Color.FromArgb(0, 0xFF, 0xCC, 0x00)
                };
                blend.Positions = new float[] { 0f, 0.25f, 0.75f, 1f };
                brush.InterpolationColors = blend;
                e.Graphics.FillRectangle(brush, bar);
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                timer.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
