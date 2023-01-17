from tkinter import *
from tkinter import messagebox, filedialog
import os
import psycopg2
import pandas as pd
from sklearn import preprocessing
from sklearn.cluster import KMeans


mydata = []
is_conn = False


# плэйсхолдер для ввода количества кластеров
class EntryWithPlaceholder(Entry):
    def __init__(self, master=None, placeholder=None):
        self.entry_var = StringVar()
        super().__init__(master, textvariable=self.entry_var)

        if placeholder is not None:
            self.placeholder = placeholder
            self.placeholder_color = 'grey'
            self.default_fg_color = self['fg']
            self.placeholder_on = False
            self.put_placeholder()

            self.entry_var.trace("w", self.entry_change)

            # При всех перечисленных событиях, если placeholder отображается, ставить курсор на 0 позицию
            self.bind("<FocusIn>", self.reset_cursor)
            self.bind("<KeyRelease>", self.reset_cursor)
            self.bind("<ButtonRelease>", self.reset_cursor)

    def entry_change(self, *args):
        if not self.get():
            self.put_placeholder()
        elif self.placeholder_on:
            self.remove_placeholder()
            self.entry_change()  # На случай, если после удаления placeholder остается пустое поле

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color
        self.icursor(0)
        self.placeholder_on = True

    def remove_placeholder(self):
        # Если был вставлен какой-то символ в начало, удаляем не весь текст, а только placeholder:
        text = self.get()[:-len(self.placeholder)]
        self.delete('0', 'end')
        self['fg'] = self.default_fg_color
        self.insert(0, text)
        self.placeholder_on = False

    def reset_cursor(self, *args):
        if self.placeholder_on:
            self.icursor(0)


# класс главного окна
class main:
    def __init__(self, master):
        self.master = master
        self.master.title('Программа клсатеризации данных')
        self.master.iconbitmap('icon.ico')
        self.master.geometry('380x210+300+225')
        self.master.resizable(False, True)
        self.master.configure(background='#f2fcfc')

        self.import_button = Button(self.master, text='Импорт CSV в БД', fg='#1b1619', bg='#87CEFA',
                                    command=self.import_csv)
        self.import_button.grid(row=0, column=0, stick='we')

        self.cluster_button = Button(self.master, text='Кластеризация данных', fg='#1b1619', bg='#87CEFA',
                                     command=self.clusterization)
        self.cluster_button.grid(row=1, column=0, stick='we')

        # Создание меню----------------------------------------------
        self.mainmenu = Menu(self.master)
        self.master.config(menu=self.mainmenu)

        self.optionsmenu = Menu(self.mainmenu, tearoff=0, bg='#f2fcfc', fg='#1b1619')
        self.optionsmenu.add_command(label="Подключение к БД", command=self.connection)
        self.optionsmenu.add_command(label="Выход", command=self.quit)

        self.mainmenu.add_cascade(label="Опции", menu=self.optionsmenu)

        self.check_button_list = []
        self.check_button_list_name = []
        # -----------------------------------------------------------

        self.var1 = BooleanVar()
        self.cluster_method = Checkbutton(self.master, text='Метод K-Means', fg='#1b1619', bg='#f2fcfc',
                                          variable=self.var1, onvalue=1, offvalue=0, command=self.show)
        self.cluster_method.grid(row=1, column=1)

        self.master.mainloop()

    # Выход из приложения
    def quit(self):
        global root
        self.conn.close()
        root.quit()

    # Указываем значение чекбокса выбора метода класстеризации
    def show(self):
        self.statement = self.var1.get()
        return self.statement

    # 1 Часть выполнения метода кластеризации; открывается файл, передаётся имя, названия столбцов и т.п;
    # создаются чекбоксы с выбором столбцов с данными для кластеризации
    def clusterization(self):
        try:
            if self.statement == 1:
                self.n_of_c = EntryWithPlaceholder(self.master, 'кол-во кластеров')
                self.n_of_c.grid(row=1, column=2)
                filename = filedialog.askopenfilename(initialdir=os.getcwd(), title='Open CSV',
                                                      filetypes=(('CSV File', '*.csv'), ('All files', '*.*')))
                self.cur_file = os.path.splitext(os.path.basename(filename))[0]
                self.df = pd.read_csv(f'{filename}')
                self.columns_names = self.df.columns
                self.labeloftables = Label(self.master, text='Выберите столбцы данных \nдля кластеризации:',
                                           background='#f2fcfc', justify=LEFT)
                self.labeloftables.grid(row=2, column=0, stick='we')
                for i in range(len(self.columns_names)):
                    self.check_button_list.append(IntVar())
                    self.check_button_list_name.append(self.df.columns[i])
                    self.cb = Checkbutton(self.master, text=f'{self.df.columns[i]}', background='#f2fcfc', onvalue=1,
                                          offvalue=0, variable=self.check_button_list[i])
                    self.cb.grid(row=i + 3, columns=1, padx=20, stick='w')
                    last = len(self.columns_names) + 4
                    self.button_execute = Button(self.master, text='Выполнить', fg='#1b1619', bg='#87CEFA',
                                                 command=self.execute)
                    self.button_execute.grid(row=last, column=0)
        except UnicodeDecodeError:
            messagebox.showerror(title='Ошибка кодировки',
                                 message='Для названий столбцов используйте названия на латинице.\n*желательно избежание пробелов в название столбцов.')

    # 2 Часть выполнения метода кластеризации; передаются значения из чекбоксов (0||1), каждому значению задаётся
    # имя столбца из списка имён столбцов. Используются методы кластеризации данных библиотеки sklearn
    # обработанные данные записываются в новый CSV файл
    def execute(self):
        try:
            self.statement_cb = []
            for i in range(len(self.check_button_list)):
                self.statement_cb.append(self.check_button_list[i].get())
            print(self.statement_cb)

            col = []
            for i in range(len(self.statement_cb)):
                if self.statement_cb[i] == 1:
                    col.append(self.check_button_list_name[i])
            print(col)
            pd.options.mode.chained_assignment = None
            self.df[col].fillna(0, inplace=True)
            # загружаем библиотеку препроцесинга данных
            # эта библиотека автоматически приведен данные к нормальным значениям (0-1)
            dataNorm = preprocessing.MinMaxScaler().fit_transform(self.df[col].values)
            # количество кластеров, которое будет использовано
            # string_clusters_num = self.n_of_c.get()
            nClust = self.n_of_c.get()
            try:
                nClust = int(self.n_of_c.get())
                km = KMeans(n_clusters=nClust)
                km.fit(dataNorm)
                labels = km.labels_ + 1
                # X = df.values[:, 1:]
                # X = np.nan_to_num(X)
                # clusterNum = 4
                # k_means = KMeans(init="k-means++", n_clusters=clusterNum, n_init=12)
                # k_means.fit(X)
                cur_com_file = (f"{self.cur_file}" + "_clustered" + ".csv")

                self.df["Clusters"] = labels
                self.df.to_csv(f"{cur_com_file}", index=False)

                messagebox.showinfo(title='Успешно', message=f'Файл {cur_com_file} создан')
            except ValueError:
                messagebox.showerror(title='Ошибка ввода',
                                     message='Введите количество кластеров')
        except ValueError:
            messagebox.showerror(title='Ошибка обработки данных',
                                 message='Проверьте значения в таблице, возможно использован строковый тип данных.\nПрограмма не может посчитать строковый тип данных.')

    # Создаётся экземпляр класса Child (окно подключения к БД)
    def connection(self):
        self.child = Child(self.master)

    # Функция импорта данных из CSV файла в новую таблицу БД.
    def import_csv(self):
        global mydata
        try:
            user = self.child.user
            self.conn = self.child.conn
            cur = self.conn.cursor()
            filename = filedialog.askopenfilename(initialdir=os.getcwd(), title='Open CSV',
                                                  filetypes=(('CSV File', '*.csv'), ('All files', '*.*')))
            table_name = os.path.splitext(os.path.basename(filename))[0]
            file = open(filename, 'r')

            # первая строка(хэдеры) названия для столбцов таблицы. Создание запроса добавления таблицы;
            # в цикле добавления имён столбцов
            lines = file.readlines()
            names = lines[0].split(',')

            # Цикл SQL запроса на создание таблицы
            for i in range(1, len(lines)):
                mydata.append(lines[i].split(','))

            query_create = f'''DROP TABLE IF EXISTS {table_name};
                            CREATE TABLE {table_name} (id SERIAL PRIMARY KEY NOT NULL,\n'''

            # Цикл SQL запроса на формирования столбцов таблицы
            for i in range(0, len(mydata[0])):
                name = names[i]
                query_create += name + ' ' + 'VARCHAR(100),\n'

            query_create = query_create[:-2]
            query_create += ');'
            cur.execute(query_create)
            self.conn.commit()

            names_for_import = ','.join(names)
            # query_insert = f"COPY {table_name} ({names_for_import}) FROM  '{filename}' DELIMITER ',' CSV HEADER;"
            # cur.execute(query_insert)
            with open(f"{filename}", 'r') as this_file:
                cur.copy_expert(f"COPY {table_name} ({names_for_import}) FROM STDOUT DELIMITER ',' CSV HEADER",
                                this_file)
            self.conn.commit()
            messagebox.showinfo(title='Успешно', message='Таблица создана')
            # conn.close()
        except Exception:
            messagebox.showerror(title='Ошибка подключения',
                                 message='Не установлено подключение к БД')


# Класс дочернего окна (подключение к БД)
class Child:
    def __init__(self, master):
        self.slave = Toplevel(master)
        self.slave.title('Подключение к БД')
        self.slave.geometry('250x160+300+225')
        self.slave.resizable(False, False)
        self.slave.configure(background='#f2fcfc')

        self.host_label = Label(self.slave, background='#f2fcfc', text='Host').grid(row=0, column=0, stick='w')
        self.database_label = Label(self.slave, background='#f2fcfc', text='Database').grid(row=1, column=0, stick='w')
        self.user_label = Label(self.slave, background='#f2fcfc', text='User').grid(row=2, column=0, stick='w')
        self.password_label = Label(self.slave, background='#f2fcfc', text='Password').grid(row=3, column=0, stick='w')
        self.port_label = Label(self.slave, background='#f2fcfc', text='Port').grid(row=4, column=0, stick='w')

        self.host_en = Entry(self.slave, width=30)
        self.host_en.grid(row=0, column=1)
        self.database_en = Entry(self.slave, width=30)
        self.database_en.grid(row=1, column=1)
        self.user_en = Entry(self.slave, width=30)
        self.user_en.grid(row=2, column=1)
        self.password_en = Entry(self.slave, width=30, show='*')
        self.password_en.grid(row=3, column=1)
        self.port_en = Entry(self.slave, width=30)
        self.port_en.grid(row=4, column=1)
        self.bnt_conn = Button(self.slave, text='Подключение', fg='#1b1619', bg='#87CEFA',
                               command=self.connection_to_db).grid(row=5, column=0,
                                                                   columnspan=2,
                                                                   pady=10)
        self.slave.grab_set()
        self.slave.focus_set()
        self.slave.wait_window()

    # Функция подключения к БД
    def connection_to_db(self):
        global is_conn
        self.user = NONE
        # Получения данных из полей ввода для входа в СУБД
        try:
            self.conn = psycopg2.connect(
                host=f"{self.host_en.get()}",
                database=f"{self.database_en.get()}",
                user=f"{self.user_en.get()}",
                password=f"{self.password_en.get()}",
                port=f"{int(self.port_en.get())}",
            )
            is_conn = True
            self.user = self.user_en.get()
            if is_conn:
                messagebox.showinfo(title='Успешно', message='Успешное подключение к БД')
                self.slave.destroy()
                return self.conn, self.user

        except psycopg2.OperationalError:
            messagebox.showerror(title='Ошибка подключения',
                                 message='Проверьте доступность хоста и корректность введённых параметров входа')
        self.host_en.delete(0, END)
        self.database_en.delete(0, END)
        self.user_en.delete(0, END)
        self.password_en.delete(0, END)
        self.port_en.delete(0, END)


# создание окна
root = Tk()

# запуск окна
main(root)
