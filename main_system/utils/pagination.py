from django.utils.safestring import mark_safe
import copy

class PageNumberPagination(object):
    def __init__(self, request, queryset, page_size=10, plus=5, page_param='page'):
        """
        :param request: 请求对象
        :param queryset: 符合条件的数据
        :param page_size: 页面显示的数据量
        :param plus: 显示前后多少页数据
        :param page_param: 在 URL 中传递的获取分页的参数
        """
        query_dict = copy.deepcopy(request.GET)
        query_dict._mutable = True
        self.query_dict = query_dict
        self.page_param = page_param

        # 获取页码
        page = request.GET.get(page_param, '1')
        if page.isdecimal():
            page = int(page)
        else:
            page = 1
        self.page = page
        self.page_size = page_size
        self.page_start = (page - 1) * self.page_size
        self.page_end = page * self.page_size

        # 获取总数并进行切片
        total_count = queryset.count()  # 在切片前获取总数量
        self.queryset = queryset[self.page_start:self.page_end]

        # 计算总页数
        total_page_count, div = divmod(total_count, self.page_size)
        if div:
            total_page_count += 1
        self.total_page_count = total_page_count
        self.plus = plus

    def html(self):
        # 计算分页范围
        if self.total_page_count <= 2 * self.plus + 1:
            start_page = 1
            end_page = self.total_page_count
        else:
            if self.page <= self.plus:
                start_page = 1
                end_page = 2 * self.plus + 1
            else:
                if (self.page + self.plus - 1) > self.total_page_count:
                    start_page = self.total_page_count - 2 * self.plus
                    end_page = self.total_page_count
                else:
                    start_page = self.page - self.plus
                    end_page = self.page + self.plus

        # 生成分页 HTML，使用 Bootstrap 样式
        page_str_list = []

        # 首页 / First Page
        self.query_dict[self.page_param] = 1
        first_page = '<li class="page-item"><a class="page-link" href="?{}">First Page</a></li>'.format(self.query_dict.urlencode())
        page_str_list.append(first_page)

        # 上一页 / Previous page
        if self.page > 1:
            self.query_dict[self.page_param] = self.page - 1
            prev = '<li class="page-item"><a class="page-link" href="?{}">Previous Page</a></li>'.format(self.query_dict.urlencode())
        else:
            prev = '<li class="page-item disabled"><a class="page-link" href="#">Previous Page</a></li>'
        page_str_list.append(prev)

        # 当前页码 / Current page numbers
        for i in range(start_page, end_page + 1):
            self.query_dict[self.page_param] = i
            if i == self.page:
                cur = '<li class="page-item active"><a class="page-link" href="?{}">{}</a></li>'.format(self.query_dict.urlencode(), i)
            else:
                cur = '<li class="page-item"><a class="page-link" href="?{}">{}</a></li>'.format(self.query_dict.urlencode(), i)
            page_str_list.append(cur)

        # 下一页 / Next page
        if self.page < self.total_page_count:
            self.query_dict[self.page_param] = self.page + 1
            nex = '<li class="page-item"><a class="page-link" href="?{}">Next Page</a></li>'.format(self.query_dict.urlencode())
        else:
            nex = '<li class="page-item disabled"><a class="page-link" href="#">Next Page</a></li>'
        page_str_list.append(nex)

        # 最后一页 / Last Page
        self.query_dict[self.page_param] = self.total_page_count
        last_page = '<li class="page-item"><a class="page-link" href="?{}">Last Page</a></li>'.format(self.query_dict.urlencode())
        page_str_list.append(last_page)

        # 添加跳转页数表单
        search_str = '''
        <form method="get" action="" class="d-inline">
            <input type="number" name="page" min="1" class="form-control d-inline w-auto" placeholder="Go to page">
            <button type="submit" class="btn btn-primary">Go</button>
        </form>
        '''
        page_str_list.append(search_str)

        # 将列表拼接成字符串并标记为安全的 HTML
        page_str = mark_safe('<ul class="pagination">' + ''.join(page_str_list) + '</ul>')
        return page_str
