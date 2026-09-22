import os
import threading
from datetime import datetime
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, DoubleVar,
    filedialog, messagebox, ttk, scrolledtext
)
from typing import List, Tuple

from src.calculator import (
    AlertType, CalculationResult, calculate, format_duration
)
from src.csv_reader import TemperatureRecord, read_csv_files, filter_by_range
from src.exporter import export_to_excel
from src.logger import get_logger
from src.range_importer import parse_range_file


class TemperatureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("温度监控数据分析工具")
        self.root.geometry("1000x750")

        self.csv_files: List[str] = []
        self.records: List[TemperatureRecord] = []
        self.results: List[Tuple[CalculationResult, str]] = []
        self.range_rows: List[dict] = []

        self.high_threshold_var = DoubleVar(value=30.0)
        self.low_threshold_var = DoubleVar(value=10.0)
        self.activation_energy_var = DoubleVar(value=83.144)
        self.csv_count_var = StringVar(value="已选: 0个文件")

        self._build_ui()

    def _build_ui(self):
        self._build_file_section()
        self._build_threshold_section()
        self._build_range_section()
        self._build_button_section()
        self._build_result_section()
        self._build_log_section()

    def _build_file_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='x')
        Label(frame, text="数据文件:", font=("Arial", 10, "bold")).pack(side='left')
        Button(frame, text="选择CSV文件", command=self._select_csv_files).pack(side='left', padx=5)
        Label(frame, textvariable=self.csv_count_var).pack(side='left', padx=5)

    def _build_threshold_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='x')
        Label(frame, text="高温阈值:", font=("Arial", 10, "bold")).pack(side='left')
        Entry(frame, textvariable=self.high_threshold_var, width=8).pack(side='left', padx=5)
        Label(frame, text="℃").pack(side='left')
        Label(frame, text="低温阈值:", font=("Arial", 10, "bold")).pack(side='left', padx=(20, 0))
        Entry(frame, textvariable=self.low_threshold_var, width=8).pack(side='left', padx=5)
        Label(frame, text="℃").pack(side='left')
        Label(frame, text="MKT活化能:", font=("Arial", 10, "bold")).pack(side='left', padx=(20, 0))
        Entry(frame, textvariable=self.activation_energy_var, width=10).pack(side='left', padx=5)
        Label(frame, text="kJ/mol").pack(side='left')

    def _build_range_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='x')
        Label(frame, text="计算区间:", font=("Arial", 10, "bold")).pack(side='left')
        Button(frame, text="导入Excel", command=self._import_ranges_from_excel).pack(side='right', padx=(5, 0))
        Button(frame, text="+ 添加区间", command=self._add_range_row).pack(side='right')

        self.range_container = Frame(frame)
        self.range_container.pack(fill='x', pady=5)

        header_frame = Frame(self.range_container)
        header_frame.pack(fill='x')
        for i, text in enumerate(["开始时间", "结束时间", "操作"]):
            Label(header_frame, text=text, font=("Arial", 9, "bold"),
                  width=25 if i < 2 else 10).grid(row=0, column=i, padx=2)

        self._add_range_row()

    def _add_range_row(self):
        row_index = len(self.range_rows)
        row_frame = Frame(self.range_container)
        row_frame.pack(fill='x', pady=2)

        start_var = StringVar(value=datetime.now().strftime("%Y-%m-%d 00:00"))
        end_var = StringVar(value=datetime.now().strftime("%Y-%m-%d 23:59"))

        Entry(row_frame, textvariable=start_var, width=25).grid(row=0, column=0, padx=2)
        Entry(row_frame, textvariable=end_var, width=25).grid(row=0, column=1, padx=2)
        Button(row_frame, text="删除", width=6,
               command=lambda: self._remove_range_row(row_index)).grid(row=0, column=2, padx=2)

        self.range_rows.append({
            'frame': row_frame,
            'start': start_var,
            'end': end_var,
        })

    def _remove_range_row(self, index):
        if len(self.range_rows) <= 1:
            messagebox.showwarning("提示", "至少需要保留一个计算区间")
            return
        row = self.range_rows[index]
        row['frame'].destroy()
        self.range_rows.remove(row)

    def _import_ranges_from_excel(self):
        filepath = filedialog.askopenfilename(
            title="选择区间Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        try:
            ranges = parse_range_file(filepath)
        except Exception as e:
            logger = get_logger()
            logger.error(f"导入区间文件失败: {e}")
            messagebox.showerror("错误", f"导入失败: {e}")
            return

        if not ranges:
            messagebox.showwarning("提示", "文件中未找到有效的区间数据")
            return

        while len(self.range_rows) > 1:
            self._remove_range_row(0)
        if self.range_rows:
            self.range_rows[0]['frame'].destroy()
            self.range_rows.clear()

        for start, end in ranges:
            self._add_range_row()
            row = self.range_rows[-1]
            row['start'].set(start.strftime("%Y-%m-%d %H:%M"))
            row['end'].set(end.strftime("%Y-%m-%d %H:%M"))

        self._log(f"已导入 {len(ranges)} 个区间")

    def _build_button_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='x')
        self.calc_button = Button(frame, text="开始计算", command=self._start_calculation,
                                  font=("Arial", 11, "bold"), bg="#4CAF50", fg="white",
                                  padx=20, pady=3)
        self.calc_button.pack(side='left')
        self.export_button = Button(frame, text="导出Excel", command=self._export_excel,
                                    font=("Arial", 10), state='disabled', padx=20, pady=3)
        self.export_button.pack(side='left', padx=10)

    def _build_result_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='both', expand=True)
        Label(frame, text="计算结果:", font=("Arial", 10, "bold")).pack(anchor='w')

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill='both', expand=True, pady=5)

    def _build_log_section(self):
        frame = Frame(self.root, padx=10, pady=5)
        frame.pack(fill='x')
        Label(frame, text="运行日志:", font=("Arial", 10, "bold")).pack(anchor='w')
        self.log_text = scrolledtext.ScrolledText(frame, height=6, font=("Consolas", 9),
                                                  state='disabled', bg="#f5f5f5")
        self.log_text.pack(fill='x')

    def _select_csv_files(self):
        files = filedialog.askopenfilenames(
            title="选择温度数据CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if files:
            self.csv_files = list(files)
            self.csv_count_var.set(f"已选: {len(self.csv_files)}个文件")
            self._log(f"已选择 {len(self.csv_files)} 个文件")
            self._load_files()

    def _load_files(self):
        self.calc_button.config(state='disabled')
        self._log("正在加载文件...")

        def worker():
            try:
                self.records = read_csv_files(self.csv_files)
                self._log(f"文件加载完成: 共 {len(self.records)} 条记录")
            except Exception as e:
                logger = get_logger()
                logger.error(f"文件加载失败: {e}")
                self._log(f"文件加载失败: {e}")
            finally:
                self.root.after(0, lambda: self.calc_button.config(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

    def _start_calculation(self):
        if not self.records:
            messagebox.showwarning("提示", "请先选择并加载CSV文件")
            return

        try:
            high = self.high_threshold_var.get()
            low = self.low_threshold_var.get()
            ea = self.activation_energy_var.get()
        except Exception:
            messagebox.showerror("错误", "阈值参数格式不正确")
            return

        if high <= low:
            messagebox.showerror("错误", "高温阈值必须大于低温阈值")
            return

        ranges = []
        for row in self.range_rows:
            try:
                start = datetime.strptime(row['start'].get().strip(), "%Y-%m-%d %H:%M")
                end = datetime.strptime(row['end'].get().strip(), "%Y-%m-%d %H:%M")
                end = end.replace(second=59)
            except ValueError:
                messagebox.showerror("错误", f"时间格式不正确，应为 YYYY-MM-DD HH:MM")
                return
            if start >= end:
                messagebox.showerror("错误", "开始时间必须早于结束时间")
                return
            ranges.append((start, end))

        self.calc_button.config(state='disabled')
        self._clear_results()
        self._log(f"开始计算 {len(ranges)} 个区间...")

        def worker():
            self.results = []
            for i, (start, end) in enumerate(ranges):
                self._log(f"正在计算区间 {i + 1}: {start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}")
                filtered = filter_by_range(self.records, start, end)
                if not filtered:
                    self._log(f"区间 {i + 1} 内无数据")
                result = calculate(filtered, high, low, ea)
                label = f"{start.strftime('%m-%d')}~{end.strftime('%m-%d')}"
                self.results.append((result, label))
                self.root.after(0, lambda r=result, l=label: self._add_result_tab(r, l))

            self._log("全部计算完成")
            self.root.after(0, lambda: self.export_button.config(state='normal'))
            self.root.after(0, lambda: self.calc_button.config(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

    def _add_result_tab(self, result, label):
        tab = Frame(self.notebook)
        self.notebook.add(tab, text=label)

        if result.statistics.data_count == 0:
            Label(tab, text="该区间内无数据", font=("Arial", 12),
                  fg="gray").pack(pady=20)
            return

        self._write_summary_tab(tab, result)
        self._write_detail_tab(tab, result)
        self._write_stats_tab(tab, result)

    def _write_summary_tab(self, parent, result):
        frame = Frame(parent, padx=10, pady=10)
        frame.pack(fill='x')
        Label(frame, text="信息汇总", font=("Arial", 11, "bold"),
              fg="#4472C4").pack(anchor='w', pady=(0, 5))

        tree = ttk.Treeview(frame, columns=("seq", "status", "duration", "pct", "count"),
                            show='headings', height=4)
        tree.heading("seq", text="序号")
        tree.heading("status", text="状态")
        tree.heading("duration", text="持续时间")
        tree.heading("pct", text="时间占比")
        tree.heading("count", text="报警次数")
        tree.column("seq", width=50, anchor='center')
        tree.column("status", width=100, anchor='center')
        tree.column("duration", width=150, anchor='center')
        tree.column("pct", width=80, anchor='center')
        tree.column("count", width=80, anchor='center')
        tree.pack(fill='x')

        for idx, s in enumerate(result.summary, 1):
            tree.insert('', 'end', values=(idx, s.status, s.duration,
                                           f"{s.percentage}%", s.alert_count))

    def _write_detail_tab(self, parent, result):
        alert_segments = [s for s in result.segments
                          if s.alert_type != AlertType.NORMAL]
        frame = Frame(parent, padx=10, pady=5)
        frame.pack(fill='both', expand=True)
        Label(frame, text="报警明细", font=("Arial", 11, "bold"),
              fg="#4472C4").pack(anchor='w', pady=(5, 0))

        tree = ttk.Treeview(frame, columns=("seq", "start", "end", "type", "duration"),
                            show='headings', height=8)
        tree.heading("seq", text="序号")
        tree.heading("start", text="开始时间")
        tree.heading("end", text="结束时间")
        tree.heading("type", text="类型")
        tree.heading("duration", text="时长")
        tree.column("seq", width=50, anchor='center')
        tree.column("start", width=150, anchor='center')
        tree.column("end", width=150, anchor='center')
        tree.column("type", width=80, anchor='center')
        tree.column("duration", width=100, anchor='center')
        tree.pack(fill='both', expand=True)

        for idx, seg in enumerate(alert_segments, 1):
            start_str = seg.start.strftime("%Y-%m-%d %H:%M:%S")
            end_str = seg.end.strftime("%Y-%m-%d %H:%M:%S")
            duration_str = format_duration(seg.duration_seconds)
            tree.insert('', 'end', values=(idx, start_str, end_str,
                                           seg.alert_type.value, duration_str))

        if not alert_segments:
            Label(frame, text="无报警记录", fg="gray").pack(pady=5)

    def _write_stats_tab(self, parent, result):
        frame = Frame(parent, padx=10, pady=5)
        frame.pack(fill='x')
        Label(frame, text="统计信息", font=("Arial", 11, "bold"),
              fg="#4472C4").pack(anchor='w', pady=(5, 0))

        stats = result.statistics
        info_text = (
            f"开始时间: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"结束时间: {stats.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"累计时长: {stats.total_duration}\n"
            f"温度最大值: {stats.temp_max}℃\n"
            f"温度最小值: {stats.temp_min}℃\n"
            f"温度平均值: {stats.temp_avg}℃\n"
            f"MKT (平均动力学温度): {stats.mkt}℃\n"
            f"数据条数: {stats.data_count}\n"
            f"\n注: MKT 用于反映产品储存或运输过程中的温度波动情况"
        )
        Label(frame, text=info_text, font=("Arial", 10), justify='left',
              anchor='w').pack(anchor='w', pady=5)

    def _clear_results(self):
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

    def _export_excel(self):
        if not self.results:
            messagebox.showwarning("提示", "请先进行计算")
            return

        filepath = filedialog.asksaveasfilename(
            title="保存Excel文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=f"温度监控报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        if not filepath:
            return

        try:
            results = [r for r, _ in self.results]
            labels = [l for _, l in self.results]
            export_to_excel(results, filepath, range_labels=labels)
            self._log(f"Excel导出完成: {os.path.basename(filepath)}")
            messagebox.showinfo("成功", f"Excel文件已保存:\n{filepath}")
        except PermissionError:
            messagebox.showerror("错误", "文件被占用，请关闭Excel后重试")
        except Exception as e:
            logger = get_logger()
            logger.error(f"导出失败: {e}")
            messagebox.showerror("错误", f"导出失败: {e}")

    def _log(self, message):
        logger = get_logger()
        logger.info(message)
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()


def run():
    root = Tk()
    app = TemperatureApp(root)
    root.mainloop()


if __name__ == '__main__':
    run()
