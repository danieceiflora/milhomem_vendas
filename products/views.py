import re
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.http import HttpResponseRedirect
from rest_framework import generics, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from rest_framework.response import Response
from app import metrics
from brands.models import Brand
from categories.models import Category
from . import models, forms, serializers


class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Product
    template_name = 'product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    permission_required = 'products.view_product'

    def get_queryset(self):
        queryset = super().get_queryset()
        title = self.request.GET.get('title')
        serie_number = self.request.GET.get('serie_number')
        category = self.request.GET.get('category')
        brand = self.request.GET.get('brand')

        if title:
            queryset = queryset.filter(title__icontains=title)
        if serie_number:
            queryset = queryset.filter(serie_number__icontains=serie_number)
        if category:
            queryset = queryset.filter(category_id=category)
        if brand:
            queryset = queryset.filter(brand__id=brand)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_metrics'] = metrics.get_product_metrics()
        context['sales_metrics'] = metrics.get_sales_metrics()
        context['categories'] = Category.objects.all()
        context['brands'] = Brand.objects.all()
        return context


class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.Product
    template_name = 'product_create.html'
    form_class = forms.ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'products.add_product'


class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Product
    template_name = 'product_detail.html'
    permission_required = 'products.view_product'


class ProductUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = models.Product
    template_name = 'product_update.html'
    form_class = forms.ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'products.change_product'


class ProductDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Product
    template_name = 'product_delete.html'
    success_url = reverse_lazy('product_list')
    permission_required = 'products.delete_product'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        block_reason = self.object.deletion_block_reason()

        if block_reason:
            messages.error(request, block_reason)
            return HttpResponseRedirect(self.get_success_url())

        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                self.object.deletion_block_reason()
                or 'Não é possível excluir este produto porque ele está relacionado a vendas ou devoluções.'
            )
            return HttpResponseRedirect(self.get_success_url())


class ProductCreateListAPIView(generics.ListCreateAPIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.ProductSerializer

    def get_queryset(self):
        queryset = models.Product.objects.all()
        search = self.request.query_params.get('search')

        if search:
            search = search.strip()
            numeric = re.sub(r'\D', '', search)
            query = Q(title__icontains=search) | Q(serie_number__icontains=search)

            if numeric:
                query |= Q(serie_number__icontains=numeric)
                try:
                    query |= Q(pk=int(numeric))
                except ValueError:
                    pass

            queryset = queryset.filter(query)

        return queryset.order_by('title')[:10]


class ProductRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = models.Product.objects.all()
    serializer_class = serializers.ProductSerializer

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        block_reason = product.deletion_block_reason()

        if block_reason:
            return Response({'detail': block_reason}, status=status.HTTP_400_BAD_REQUEST)

        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'detail': block_reason
                    or 'Não é possível excluir este produto porque ele está relacionado a vendas ou devoluções.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
