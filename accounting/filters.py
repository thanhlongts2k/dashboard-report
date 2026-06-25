from django_filters import rest_framework as filters
from django.db.models import Q
from datetime import datetime
from .models import BUPerformanceDaily, BUPerformance

class BUPerformanceDailyFilter(filters.FilterSet):
    # Filter theo quãng ngày (chấp nhận format YYYY-MM-DD)
    start_date = filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="date", lookup_expr="lte")
    
    # Filter theo tuần, tháng, năm thông qua các lookup_expr của Django ORM
    week = filters.NumberFilter(field_name="date", lookup_expr="week")
    month = filters.NumberFilter(field_name="date", lookup_expr="month")
    year = filters.NumberFilter(field_name="date", lookup_expr="year")
    
    # Custom logic cho bu_id giống như code cũ của fen
    bu_id = filters.CharFilter(method='filter_by_bu')

    class Meta:
        model = BUPerformanceDaily
        fields = ['start_date', 'end_date', 'week', 'month', 'year', 'bu_id']

    def filter_by_bu(self, queryset, name, value):
        if value and value.lower() not in ['0', 'null', 'none']:
            return queryset.filter(performance_month__business_unit_id=value)
        # Mặc định lọc theo Tổng công ty nếu không truyền hoặc truyền giá trị rỗng/0
        return queryset.filter(performance_month__business_unit__isnull=True)


class BUPerformanceFilter(filters.FilterSet):
    start_date = filters.DateFilter(method='filter_by_start_date')
    end_date = filters.DateFilter(method='filter_by_end_date')
    month = filters.NumberFilter(field_name="month", lookup_expr="exact")
    year = filters.NumberFilter(field_name="year", lookup_expr="exact")
    bu_id = filters.CharFilter(method='filter_by_bu')
    only_roots = filters.CharFilter(method='filter_only_roots')

    class Meta:
        model = BUPerformance
        fields = ['start_date', 'end_date', 'month', 'year', 'bu_id', 'only_roots']

    def filter_by_start_date(self, queryset, name, value):
        if value:
            # Lọc bản ghi có năm lớn hơn, hoặc cùng năm nhưng tháng lớn hơn/bằng
            return queryset.filter(
                Q(year__gt=value.year) | Q(year=value.year, month__gte=value.month)
            )
        return queryset

    def filter_by_end_date(self, queryset, name, value):
        if value:
            # Lọc bản ghi có năm nhỏ hơn, hoặc cùng năm nhưng tháng nhỏ hơn/bằng
            return queryset.filter(
                Q(year__lt=value.year) | Q(year=value.year, month__lte=value.month)
            )
        return queryset

    def filter_by_bu(self, queryset, name, value):
        if value == 'all':
            return queryset
        if value == 'null' or value == '':
            return queryset.filter(business_unit__isnull=True)
        return queryset.filter(business_unit_id=value)

    def filter_only_roots(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(business_unit__parent__isnull=True)
        return queryset