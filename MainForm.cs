using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.NetworkInformation;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

namespace DotNetRuntimeInstaller
{
    public partial class MainForm : Form
    {
        // JSON mapping classes
        public class ReleaseIndex
        {
            [JsonPropertyName("releases")]
            public List<Release> Releases { get; set; } = new();
        }

        public class Release
        {
            [JsonPropertyName("release-version")]
            public string ReleaseVersion { get; set; } = string.Empty;

            [JsonPropertyName("runtime")]
            public RuntimeInfo Runtime { get; set; } = new RuntimeInfo();
        }

        public class RuntimeInfo
        {
            [JsonPropertyName("files")]
            public List<RuntimeFile> Files { get; set; } = new();
        }

        public class RuntimeFile
        {
            [JsonPropertyName("name")]
            public string Name { get; set; } = string.Empty;

            [JsonPropertyName("rid")]
            public string Rid { get; set; } = string.Empty;

            [JsonPropertyName("url")]
            public string Url { get; set; } = string.Empty;
        }

        private readonly Dictionary<string, string> _versionMetadataUrls = new()
        {
            { "5.0", "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/5.0/releases.json" },
            { "6.0", "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/6.0/releases.json" },
            { "7.0", "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/7.0/releases.json" },
            { "8.0", "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/8.0/releases.json" },
            { "9.0", "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/9.0/releases.json" }
        };

        private readonly HttpClient _httpClient = new();
        private bool _isDarkMode = false;

        public MainForm()
        {
            InitializeComponent();
            CreateInstallButtons();

            // "Eski .NET Sürümlerini Kaldır" butonu
            var btnClean = new Button
            {
                Text = "Eski .NET Sürümlerini Kaldır",
                AutoSize = true,
                Margin = new Padding(3)
            };
            btnClean.Click += async (s, e) => await DeleteOldRuntimesAsync();
            bottomLeftFlowLayoutPanel.Controls.Add(btnClean);

            btnRefresh.Click += async (s, e) => await CheckInstalledRuntimesAsync();
            themeToggleButton.Click += (s, e) => ToggleTheme(false);

            Load += async (s, e) =>
            {
                ToggleTheme(true);
                await CheckInstalledRuntimesAsync();
            };
        }

        private void CreateInstallButtons()
        {
            var panel = rightColumnTableLayoutPanel;
            panel.SuspendLayout();
            string[] versions = { "5.0", "6.0", "7.0", "8.0", "9.0" };
            int tabIndex = 1;
            for (int i = 0; i < versions.Length; i++)
            {
                var ver = versions[i];
                var btn64 = new Button
                {
                    Text = $".NET {ver} (x64)",
                    Dock = DockStyle.Fill,
                    TabIndex = tabIndex++
                };
                btn64.Click += async (_, __) => await DownloadAndInstallRuntimeAsync(ver, true);
                panel.Controls.Add(btn64, 0, i);

                var btn32 = new Button
                {
                    Text = $".NET {ver} (x86)",
                    Dock = DockStyle.Fill,
                    TabIndex = tabIndex++
                };
                btn32.Click += async (_, __) => await DownloadAndInstallRuntimeAsync(ver, false);
                panel.Controls.Add(btn32, 1, i);
            }
            panel.ResumeLayout();
        }

        private async Task CheckInstalledRuntimesAsync()
        {
            SetUiState(false, "Yenileniyor...");
            runtimeListBox.Items.Clear();
            try
            {
                var hosts = new List<(string exe, string bit)> { ("dotnet", "x64") };
                var x86Path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "dotnet", "dotnet.exe");
                if (File.Exists(x86Path)) hosts.Add((x86Path, "x86"));

                var seen = new HashSet<(string version, string bit)>();
                var rx = new Regex("^(?<name>\\S+)\\s+(?<version>\\S+)\\s+\\[(?<path>.+)\\]$");
                foreach (var (exe, bit) in hosts)
                {
                    var psi = new ProcessStartInfo(exe, "--list-runtimes")
                    {
                        RedirectStandardOutput = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };
                    using var proc = Process.Start(psi);
                    if (proc == null) continue;
                    var output = await proc.StandardOutput.ReadToEndAsync();
                    await proc.WaitForExitAsync();
                    foreach (var line in output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
                    {
                        var m = rx.Match(line);
                        if (!m.Success) continue;
                        var version = m.Groups["version"].Value;
                        if (seen.Add((version, bit)))
                            runtimeListBox.Items.Add($".NET {version} ({bit})");
                    }
                }
                if (runtimeListBox.Items.Count == 0)
                    runtimeListBox.Items.Add("Hiçbir .NET Runtime bulunamadı.");
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, $"Listeleme hatası: {ex.Message}", "Hata", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                progressBar.Value = 0;
                SetUiState(true, "Hazır.");
            }
        }

        private async Task DeleteOldRuntimesAsync()
        {
            progressBar.Visible = true;
            progressBar.Value = 0;
            SetUiState(false, "Eski sürümler taranıyor...");

            var installed = GetInstalledDotNetRuntimes().ToList();
            var toKeep = installed
                .GroupBy(x => string.Join('.', x.Version.Split('.').Take(2)))
                .Select(g => g.OrderByDescending(x => new Version(x.Version)).First())
                .ToHashSet();
            var toRemove = installed.Except(toKeep).ToList();

            if (toRemove.Count == 0)
            {
                SetUiState(true, "Kaldırılacak eski sürüm yok.");
                progressBar.Visible = false;
                return;
            }

            for (int i = 0; i < toRemove.Count; i++)
            {
                var (version, productCode) = toRemove[i];
                string uninstallCmd = null;
                foreach (var view in Environment.Is64BitOperatingSystem
                    ? new[] { RegistryView.Registry64, RegistryView.Registry32 }
                    : new[] { RegistryView.Registry32 })
                {
                    using var baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view);
                    using var key = baseKey.OpenSubKey($"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{productCode}");
                    uninstallCmd = key?.GetValue("UninstallString") as string;
                    if (!string.IsNullOrEmpty(uninstallCmd)) break;
                }

                var percent = (int)((i + 1) * 100.0 / toRemove.Count);
                statusLabel.Text = $"{version} sürümü bulundu, kaldırma işlemine başlanıyor...";
                progressBar.Value = percent;

                if (!string.IsNullOrEmpty(uninstallCmd))
                {
                    var parts = uninstallCmd.Split(new[] { ' ' }, 2);
                    var exe = parts[0].Trim('"');
                    var args = (parts.Length > 1 ? parts[1] : "") + " /quiet /norestart";
                    var psi = new ProcessStartInfo(exe, args)
                    {
                        UseShellExecute = true,
                        Verb = "runas"
                    };
                    using var p = Process.Start(psi);
                    if (p != null)
                        await p.WaitForExitAsync();
                }

                statusLabel.Text = $"{version} kaldırıldı. ({percent}%)";
            }

            await CheckInstalledRuntimesAsync();
            statusLabel.Text = "Eski sürümler kaldırıldı.";
            SetUiState(true, "Hazır.");
            progressBar.Visible = false;
        }

        private IEnumerable<(string Version, string ProductCode)> GetInstalledDotNetRuntimes()
        {
            var list = new List<(string, string)>();
            RegistryView[] views = Environment.Is64BitOperatingSystem
                ? new[] { RegistryView.Registry64, RegistryView.Registry32 }
                : new[] { RegistryView.Registry32 };

            foreach (var view in views)
            {
                using var baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view);
                using var uninstallKey = baseKey.OpenSubKey("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall");
                if (uninstallKey == null) continue;
                foreach (var sub in uninstallKey.GetSubKeyNames())
                {
                    using var sk = uninstallKey.OpenSubKey(sub);
                    var displayName = sk?.GetValue("DisplayName") as string;
                    var displayVersion = sk?.GetValue("DisplayVersion") as string;
                    if (displayName != null && displayName.StartsWith("Microsoft .NET Runtime ") && !string.IsNullOrEmpty(displayVersion))
                    {
                        list.Add((displayVersion, sub));
                    }
                }
            }
            return list;
        }

        public async Task DownloadAndInstallRuntimeAsync(string versionKey, bool isX64)
        {
            SetUiState(false, "Kurulum hazırlığı...");
            try
            {
                if (!await IsConnectedToInternetAsync())
                {
                    MessageBox.Show(this, "Lütfen internet bağlantınızı kontrol edin.", "Bağlantı Hatası", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                if (!_versionMetadataUrls.TryGetValue(versionKey, out var metaUrl)) return;
                var json = await _httpClient.GetStringAsync(metaUrl);
                var idx = JsonSerializer.Deserialize<ReleaseIndex>(json)!;
                var rel = idx.Releases.FirstOrDefault();
                if (rel == null)
                {
                    MessageBox.Show(this, "Sürüm bilgisi alınamadı.", "Hata", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                var file = rel.Runtime.Files.FirstOrDefault(f => f.Rid.Contains(isX64 ? "x64" : "x86") && f.Name.EndsWith(".exe"));
                if (file == null)
                {
                    MessageBox.Show(this, "Uygun installer bulunamadı.", "Hata", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                var temp = Path.Combine(Path.GetTempPath(), file.Name);
                await DownloadFileWithProgressAsync(file.Url, temp);

                var args = silentCheckBox.Checked ? "/install /quiet /norestart" : "/install";
                var psi = new ProcessStartInfo(temp, args) { UseShellExecute = true, Verb = "runas" };
                using var inst = Process.Start(psi);
                if (inst != null)
                {
                    await inst.WaitForExitAsync();
                    var code = inst.ExitCode;
                    var msg = code switch
                    {
                        0 => $".NET {rel.ReleaseVersion} kuruldu.",
                        3010 => $".NET {rel.ReleaseVersion} kuruldu. Sistem yeniden başlatılmalı.",
                        _ => $"Kurulum tamamlandı; çıkış kodu: {code}."
                    };
                    MessageBox.Show(this, msg, "Bilgi", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }

                await CheckInstalledRuntimesAsync();
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, $"Kurulum hatası:\n{ex.Message}", "Hata", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                SetUiState(true, "Hazır.");
            }
        }

        private async Task DownloadFileWithProgressAsync(string url, string dest)
        {
            using var res = await _httpClient.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
            res.EnsureSuccessStatusCode();
            var total = res.Content.Headers.ContentLength ?? -1L;
            var read = 0L;
            using var strm = await res.Content.ReadAsStreamAsync();
            using var fs = new FileStream(dest, FileMode.Create, FileAccess.Write, FileShare.None, 8192, true);
            var buf = new byte[8192];
            int br;
            while ((br = await strm.ReadAsync(buf, 0, buf.Length)) > 0)
            {
                await fs.WriteAsync(buf, 0, br);
                read += br;
                if (total > 0) progressBar.Value = (int)((double)read / total * 100);
            }
        }

        private void SetUiState(bool en, string st)
        {
            if (InvokeRequired) { Invoke(new Action(() => SetUiState(en, st))); return; }
            foreach (var btn in rightColumnTableLayoutPanel.Controls.OfType<Button>()) btn.Enabled = en;
            foreach (var btn in bottomLeftFlowLayoutPanel.Controls.OfType<Button>()) btn.Enabled = en;
            silentCheckBox.Enabled = en;
            progressBar.Visible = !en;
            statusLabel.Text = st;
        }

        private async Task<bool> IsConnectedToInternetAsync()
        {
            try
            {
                using var ping = new Ping();
                var reply = await ping.SendPingAsync("1.1.1.1", 2000);
                return reply.Status == IPStatus.Success;
            }
            catch
            {
                return false;
            }
        }

        // Designer event handlers
        private async void btnRefresh_Click(object sender, EventArgs e) => await CheckInstalledRuntimesAsync();
        private void themeToggleButton_Click(object sender, EventArgs e) => ToggleTheme(false);

        private void ToggleTheme(bool init)
        {
            if (!init) _isDarkMode = !_isDarkMode;

            Color bg = _isDarkMode ? Color.FromArgb(30, 30, 30) : SystemColors.Control;
            Color fg = _isDarkMode ? Color.White : SystemColors.ControlText;
            Color btnBg = _isDarkMode ? Color.FromArgb(45, 45, 45) : SystemColors.ControlLight;
            Color listBg = _isDarkMode ? Color.FromArgb(50, 50, 50) : SystemColors.Window;

            BackColor = bg;
            mainTableLayoutPanel.BackColor = bg;
            rightColumnTableLayoutPanel.BackColor = bg;
            bottomLeftFlowLayoutPanel.BackColor = bg;
            leftColumnPanel.BackColor = bg;

            runtimeListBox.BackColor = listBg;
            runtimeListBox.ForeColor = fg;

            var buttons = rightColumnTableLayoutPanel.Controls.OfType<Button>()
                .Concat(bottomLeftFlowLayoutPanel.Controls.OfType<Button>());
            foreach (var btn in buttons)
            {
                btn.BackColor = btnBg;
                btn.ForeColor = fg;
                btn.FlatAppearance.BorderColor = _isDarkMode ? Color.FromArgb(80, 80, 80) : Color.Gray;
                btn.FlatStyle = FlatStyle.Flat;
            }

            statusStrip.BackColor = bg;
            statusStrip.ForeColor = fg;
            themeToggleButton.Text = _isDarkMode ? "Açık Mod" : "Koyu Mod";
        }
    }
}
