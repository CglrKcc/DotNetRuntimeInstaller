namespace DotNetRuntimeInstaller
{
    partial class MainForm
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            this.mainTableLayoutPanel = new System.Windows.Forms.TableLayoutPanel();
            this.leftColumnPanel = new System.Windows.Forms.Panel();
            this.runtimeListBox = new System.Windows.Forms.ListBox();
            this.bottomLeftFlowLayoutPanel = new System.Windows.Forms.FlowLayoutPanel();
            this.themeToggleButton = new System.Windows.Forms.Button();
            this.btnRefresh = new System.Windows.Forms.Button();
            this.rightColumnTableLayoutPanel = new System.Windows.Forms.TableLayoutPanel();
            this.silentCheckBox = new System.Windows.Forms.CheckBox();
            this.offlineCheckBox = new System.Windows.Forms.CheckBox();
            this.progressBar = new System.Windows.Forms.ProgressBar();
            this.statusStrip = new System.Windows.Forms.StatusStrip();
            this.statusLabel = new System.Windows.Forms.ToolStripStatusLabel();
            // 
            // mainTableLayoutPanel
            // 
            this.mainTableLayoutPanel.ColumnCount = 2;
            this.mainTableLayoutPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 50F));
            this.mainTableLayoutPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 50F));
            this.mainTableLayoutPanel.Controls.Add(this.leftColumnPanel, 0, 0);
            this.mainTableLayoutPanel.Controls.Add(this.rightColumnTableLayoutPanel, 1, 0);
            this.mainTableLayoutPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.mainTableLayoutPanel.Location = new System.Drawing.Point(0, 0);
            this.mainTableLayoutPanel.Name = "mainTableLayoutPanel";
            this.mainTableLayoutPanel.RowCount = 1;
            this.mainTableLayoutPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 100F));
            this.mainTableLayoutPanel.Size = new System.Drawing.Size(800, 450);
            // 
            // leftColumnPanel
            // 
            this.leftColumnPanel.Controls.Add(this.runtimeListBox);
            this.leftColumnPanel.Controls.Add(this.bottomLeftFlowLayoutPanel);
            this.leftColumnPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.leftColumnPanel.Location = new System.Drawing.Point(3, 3);
            this.leftColumnPanel.Name = "leftColumnPanel";
            this.leftColumnPanel.Size = new System.Drawing.Size(394, 444);
            // 
            // runtimeListBox
            // 
            this.runtimeListBox.Dock = System.Windows.Forms.DockStyle.Fill;
            this.runtimeListBox.FormattingEnabled = true;
            this.runtimeListBox.ItemHeight = 16;
            this.runtimeListBox.Location = new System.Drawing.Point(0, 0);
            this.runtimeListBox.Name = "runtimeListBox";
            this.runtimeListBox.Size = new System.Drawing.Size(394, 380);
            // 
            // bottomLeftFlowLayoutPanel
            // 
            this.bottomLeftFlowLayoutPanel.Controls.Add(this.themeToggleButton);
            this.bottomLeftFlowLayoutPanel.Controls.Add(this.btnRefresh);
            this.bottomLeftFlowLayoutPanel.Dock = System.Windows.Forms.DockStyle.Bottom;
            this.bottomLeftFlowLayoutPanel.FlowDirection = System.Windows.Forms.FlowDirection.LeftToRight;
            this.bottomLeftFlowLayoutPanel.Location = new System.Drawing.Point(0, 380);
            this.bottomLeftFlowLayoutPanel.Name = "bottomLeftFlowLayoutPanel";
            this.bottomLeftFlowLayoutPanel.Size = new System.Drawing.Size(394, 64);
            // 
            // themeToggleButton
            // 
            this.themeToggleButton.AutoSize = true;
            this.themeToggleButton.AutoSizeMode = System.Windows.Forms.AutoSizeMode.GrowAndShrink;
            this.themeToggleButton.Location = new System.Drawing.Point(3, 3);
            this.themeToggleButton.Name = "themeToggleButton";
            this.themeToggleButton.Size = new System.Drawing.Size(94, 30);
            this.themeToggleButton.Text = "Koyu Mod";
            // 
            // btnRefresh
            // 
            this.btnRefresh.AutoSize = true;
            this.btnRefresh.AutoSizeMode = System.Windows.Forms.AutoSizeMode.GrowAndShrink;
            this.btnRefresh.Location = new System.Drawing.Point(103, 3);
            this.btnRefresh.Name = "btnRefresh";
            this.btnRefresh.Size = new System.Drawing.Size(120, 30);
            this.btnRefresh.Text = "Listeyi Yenile";
            // 
            // rightColumnTableLayoutPanel
            // 
            this.rightColumnTableLayoutPanel.ColumnCount = 2;
            this.rightColumnTableLayoutPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 50F));
            this.rightColumnTableLayoutPanel.ColumnStyles.Add(new System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 50F));
            this.rightColumnTableLayoutPanel.Dock = System.Windows.Forms.DockStyle.Fill;
            this.rightColumnTableLayoutPanel.Location = new System.Drawing.Point(403, 3);
            this.rightColumnTableLayoutPanel.Name = "rightColumnTableLayoutPanel";
            this.rightColumnTableLayoutPanel.RowCount = 7;
            for (int i = 0; i < 5; i++)
                this.rightColumnTableLayoutPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 50F));
            this.rightColumnTableLayoutPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 30F));
            this.rightColumnTableLayoutPanel.RowStyles.Add(new System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 30F));
            this.rightColumnTableLayoutPanel.Size = new System.Drawing.Size(394, 444);
            // 
            // silentCheckBox
            // 
            this.silentCheckBox.AutoSize = true;
            this.silentCheckBox.Location = new System.Drawing.Point(3, 253);
            this.silentCheckBox.Name = "silentCheckBox";
            this.silentCheckBox.Size = new System.Drawing.Size(107, 21);
            this.silentCheckBox.Text = "Sessiz Kurulum";
            // 
            // offlineCheckBox
            // 
            this.offlineCheckBox.AutoSize = true;
            this.offlineCheckBox.Location = new System.Drawing.Point(3, 283);
            this.offlineCheckBox.Name = "offlineCheckBox";
            this.offlineCheckBox.Size = new System.Drawing.Size(101, 21);
            this.offlineCheckBox.Text = "Offline Mod";
            this.offlineCheckBox.Enabled = false;
            // 
            // progressBar
            // 
            this.progressBar.Dock = System.Windows.Forms.DockStyle.Bottom;
            this.progressBar.Location = new System.Drawing.Point(0, 420);
            this.progressBar.Name = "progressBar";
            this.progressBar.Size = new System.Drawing.Size(394, 24);
            // 
            // statusStrip
            // 
            this.statusStrip.Dock = System.Windows.Forms.DockStyle.Bottom;
            this.statusStrip.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.statusLabel});
            this.statusStrip.Location = new System.Drawing.Point(0, 450);
            this.statusStrip.Name = "statusStrip";
            this.statusStrip.Size = new System.Drawing.Size(800, 22);
            // 
            // statusLabel
            // 
            this.statusLabel.Name = "statusLabel";
            this.statusLabel.Size = new System.Drawing.Size(39, 17);
            this.statusLabel.Text = "Hazır.";
            // 
            // MainForm
            // 
            this.ClientSize = new System.Drawing.Size(800, 472);
            this.Controls.Add(this.mainTableLayoutPanel);
            this.Controls.Add(this.statusStrip);
            this.Name = "MainForm";
            this.Text = ".NET Runtime Installer by Çağlar";

            this.mainTableLayoutPanel.ResumeLayout(false);
            this.leftColumnPanel.ResumeLayout(false);
            this.bottomLeftFlowLayoutPanel.ResumeLayout(false);
            this.bottomLeftFlowLayoutPanel.PerformLayout();
            this.statusStrip.ResumeLayout(false);
            this.statusStrip.PerformLayout();
        }

        private System.Windows.Forms.TableLayoutPanel mainTableLayoutPanel;
        private System.Windows.Forms.Panel leftColumnPanel;
        private System.Windows.Forms.ListBox runtimeListBox;
        private System.Windows.Forms.FlowLayoutPanel bottomLeftFlowLayoutPanel;
        private System.Windows.Forms.Button themeToggleButton;
        private System.Windows.Forms.Button btnRefresh;
        private System.Windows.Forms.TableLayoutPanel rightColumnTableLayoutPanel;
        private System.Windows.Forms.CheckBox silentCheckBox;
        private System.Windows.Forms.CheckBox offlineCheckBox;
        private System.Windows.Forms.ProgressBar progressBar;
        private System.Windows.Forms.StatusStrip statusStrip;
        private System.Windows.Forms.ToolStripStatusLabel statusLabel;

        #endregion
    }
}
