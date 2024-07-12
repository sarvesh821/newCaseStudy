from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from .forms import (
    AdminAttributesRatingForm,
    AdminTaskRatingForm,
    RegisterEmployeeForm,
    TaskForm,
)
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Attributes, Employee, Task, User
from Api.serializers import EmployeeSerializer ,TaskSerializer
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.http import JsonResponse

def get_csrf_token(request):
    token = get_token(request)
    response = JsonResponse({'csrfToken': token})
    response.set_cookie('csrftoken', token)  
    return response



def BASE(request):
    return render(request, "firstPage.html")


@api_view(['POST'])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'message': 'Login successful', 'is_staff': user.is_staff,'token':token.key}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)




    
   
        
        


@api_view(['GET'])
@permission_classes([IsAuthenticated])

def employee_detail(request):
    employee = Employee.objects.get(user=request.user)
    serializer = EmployeeSerializer(employee)
    return Response(serializer.data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_tasks(request):
    print(f"Authenticated user: {request.user}")
    if request.user.is_authenticated:
        print("User is authenticated")
    else:
        print("User is not authenticated")

    try:
        employee = request.user.employee
        tasks_to_rate = Task.objects.filter(employee=employee, rating=None,is_appraisable=True )
        rated_tasks = Task.objects.filter(employee=employee).exclude(rating=None)

        tasks_to_rate_serializer = TaskSerializer(tasks_to_rate, many=True)
        rated_tasks_serializer = TaskSerializer(rated_tasks, many=True)

        return Response({
            'tasks_to_rate': tasks_to_rate_serializer.data,
            'rated_tasks': rated_tasks_serializer.data,
        })
    except Task.DoesNotExist:
        return Response({'error': 'Tasks not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_task(request):
    form = TaskForm(request.data)
    if form.is_valid():
        task = form.save(commit=False)
        task.employee = request.user.employee
        task.save()
        return Response({'message': 'Task created successfully'}, status=status.HTTP_201_CREATED)
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)  


@login_required
@csrf_exempt
def send_tasks_for_appraisal(request):
    if request.method == "POST":
        employee = request.user.employee
        tasks = Task.objects.filter(employee=employee, is_appraisable=True,rating__isnull=True)
        if not tasks.exists():
            return JsonResponse({'error': 'No tasks available for appraisal'}, status=404)
        tasks.update(is_appraisable=False)
        return JsonResponse({'message': 'Tasks sent for appraisal successfully'}, status=200)
    return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    

@api_view(['POST'])
def register_employee(request):
   
    user_data = {
        'username': request.data.get('username'),
        'email': request.data.get('email'),
        'password': request.data.get('password')
    }
    
  
    user = User.objects.create_user(
        username=user_data['username'],
        email=user_data['email'],
        password=user_data['password']
    )
    
  
    employee_data = {
        'user': user.id,  
        'date_of_joining': request.data.get('dateOfJoining'),
        'designation': request.data.get('designation'),
        'contact_no': request.data.get('contactNo'),
        'role': request.data.get('role'),
        'email': request.data.get('email'),
        'first_name': request.data.get('firstName'),
        'last_name': request.data.get('lastName')
    }
    

    serializer = EmployeeSerializer(data=employee_data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED,)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def current_employees(request):
    employees_count = Employee.objects.count()
    return Response({'count': employees_count})



@api_view(['GET'])
def employees_with_unrated_tasks_count(request):
    one_year_ago = timezone.now().date() - timedelta(days=365)
    employees = Employee.objects.filter(Q(task__is_appraisable=True) & Q(task__rating__isnull=True) & Q(date_of_joining__lte=one_year_ago)).distinct()
    count = employees.count()
    return Response({'count': count})



@api_view(['GET'])
def EmployeesWithTasksForRating(request):
    one_year_ago = timezone.now().date() - timedelta(days=365)
    employees = Employee.objects.filter(Q(task__is_appraisable=True) & Q(task__rating__isnull=True) & Q(date_of_joining__lte=one_year_ago)).distinct()
    serializer = EmployeeSerializer(employees, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_employee_tasks(request, employee_id):
    try:
        tasks = Task.objects.filter(employee__id=employee_id,rating__isnull=True)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    except Task.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def save_task_rating(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

    rating = request.data.get('rating')
    if rating is not None and 0 <= rating <= 5:
        task.rating = rating
        task.save()
        return Response({'message': 'Task rating saved successfully'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid rating value'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def save_attribute_ratings(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.get('attributes', [])
    if len(data) != 10:
        return Response({'error': 'Exactly 10 attribute ratings are required'}, status=status.HTTP_400_BAD_REQUEST)

    attributes, created = Attributes.objects.get_or_create(employee=employee)
    attributes.time_management = data[0]
    attributes.communication = data[1]
    attributes.creativity = data[2]
    attributes.respect_of_deadlines = data[3]
    attributes.ability_to_plan = data[4]
    attributes.problem_solving = data[5]
    attributes.passion_to_work = data[6]
    attributes.confidence = data[7]
    attributes.adaptable = data[8]
    attributes.learning_power = data[9]
    attributes.save()

    return Response({'message': 'Attribute ratings saved successfully'}, status=status.HTTP_200_OK)



@api_view(['GET'])
def get_employee_details(request, id):
    try:
        employee = Employee.objects.get(id=id)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Employee.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)




















