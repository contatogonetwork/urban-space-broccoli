from datetime import date

class MockStreamlit:
    """
    Mock para o Streamlit para testes.
    Fornece uma implementação simulada das funções do Streamlit.
    """
    def __init__(self):
        self.items = {}
        self.markdown_calls = []
        self.title_calls = []
        self.header_calls = []
        self.dataframe_calls = []
        self.form_vals = {}
        self.sidebar_items = []
        self.input_calls = {}
        self.form_submitted = {}
        
    def title(self, text):
        self.title_calls.append(text)
        return text
        
    def header(self, text):
        self.header_calls.append(text)
        
    def markdown(self, text):
        self.markdown_calls.append(text)
        
    def dataframe(self, df, **kwargs):
        self.dataframe_calls.append(df)
        
    def sidebar(self):
        return self
        
    def form(self, key):
        return self
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def form_submit_button(self, label):
        return self.form_submitted.get(label, False)
        
    def text_input(self, label, value="", **kwargs):
        return self.items.get(label, value)
        
    def number_input(self, label, **kwargs):
        return self.input_calls.get(label, kwargs.get('value', 0))
        
    def date_input(self, label, **kwargs):
        return self.input_calls.get(label, kwargs.get('value', date.today()))
        
    def selectbox(self, label, options, **kwargs):
        default = options[0] if options else None
        return self.items.get(label, default)
        
    def checkbox(self, label, **kwargs):
        return self.items.get(label, kwargs.get('value', False))
        
    def radio(self, label, options, **kwargs):
        default = options[0] if options else None
        return self.items.get(label, default)
        
    def success(self, text):
        self.items['success'] = text
        
    def error(self, text):
        self.items['error'] = text
        
    def info(self, text):
        self.items['info'] = text
        
    def warning(self, text):
        self.items['warning'] = text
        
    def columns(self, num_cols):
        class MockColumn:
            def __init__(self):
                self.content = []
                
            def __enter__(self):
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
                
            def selectbox(self, label, options, **kwargs):
                default = options[0] if options else None
                return default
                
            def number_input(self, label, **kwargs):
                return kwargs.get('value', 0)
                
            def date_input(self, label, **kwargs):
                return kwargs.get('value', date.today())
                
            def metric(self, label, value, **kwargs):
                pass
                
            def write(self, content):
                self.content.append(content)
                
            def text(self, content):
                self.content.append(content)
        
        return [MockColumn() for _ in range(num_cols if isinstance(num_cols, int) else len(num_cols))]
        
    def set_form_submitted(self, label, value=True):
        self.form_submitted[label] = value
        
    def set_input(self, label, value):
        self.input_calls[label] = value
        
    def subheader(self, text):
        self.items['subheader'] = text
        
    def write(self, text):
        self.items['write'] = text
        
    def expander(self, title):
        return self
