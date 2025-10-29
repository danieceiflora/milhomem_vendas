import re
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from rest_framework import generics, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Customer
from .forms import CustomerForm
from .serializers import CustomerSerializer


class CustomerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Customer
    template_name = 'customer_list.html'
    context_object_name = 'customers'
    paginate_by = 10
    permission_required = 'customers.view_customer'

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.GET.get('name')
        email = self.request.GET.get('email')

        if name:
            queryset = queryset.filter(full_name__icontains=name)
        if email:
            queryset = queryset.filter(email__icontains=email)

        return queryset


class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Customer
    template_name = 'customer_create.html'
    form_class = CustomerForm
    success_url = reverse_lazy('customer_list')
    permission_required = 'customers.add_customer'


class CustomerDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Customer
    template_name = 'customer_detail.html'
    permission_required = 'customers.view_customer'


class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Customer
    template_name = 'customer_update.html'
    form_class = CustomerForm
    success_url = reverse_lazy('customer_list')
    permission_required = 'customers.change_customer'


class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customer_delete.html'
    success_url = reverse_lazy('customer_list')
    permission_required = 'customers.delete_customer'


class CustomerListCreateAPIView(generics.ListCreateAPIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.query_params.get('search')

        if search:
            search = search.strip()
            numeric = re.sub(r'\D', '', search)
            query = Q(full_name__icontains=search) | Q(email__icontains=search)
            if numeric:
                query |= Q(cpf__icontains=numeric) | Q(phone__icontains=numeric)
            else:
                query |= Q(cpf__icontains=search) | Q(phone__icontains=search)
            queryset = queryset.filter(query)

        return queryset.order_by('full_name')[:10]


class CustomerRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
