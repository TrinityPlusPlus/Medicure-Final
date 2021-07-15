from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from doctor.models import DoctorInfo
from django.contrib.auth.models import User
from django.contrib import messages
from doctor.forms import UserForm
from appointment.forms import AddAppointmentForm
from django.db.models import Q

from Health.forms import *
from patient.heart import pred_heart
from patient.image_block import predImageBlock
from patient.Diabetes import pred_diabetes
from patient.pneumonia import pred1
from api.diseaseml import pred

from django.contrib.auth.decorators import user_passes_test, login_required
from patient.models import *
# Create your views here.
from doctor.doctor_decorators import unauthenticated_doctor,allowed_users
from django.contrib.auth.decorators import login_required

from appointment.models import AppointmentDetails,BookedAppointment

##Email Send
from django.core.mail import send_mail
from Disease.settings import EMAIL_HOST_USER
from django.template.loader import render_to_string


@unauthenticated_doctor
def doctor_login(request):
    if request.method=="POST":
        username = request.POST.get('username')       
        password = request.POST.get('password') 
        user =authenticate(request, username=username, password=password)
        if user is not None:
            login(request,user)
            return redirect('dashboard_doctor')
        else:
            messages.info(request, "Please enter valid credentials")
            
            return render(request, 'doctor/login.html')
    else:
        return render(request, 'doctor/login.html')

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def prescription(request):
    if request.method=="GET":
        return render(request, "doctor/prescription_form.html")
    else:
        email = request.POST.get("email")
        prescription = request.POST.get('prescription')
        doctor = User.objects.filter(id=request.user.id).first()
        print('prescription')
        print(prescription)
        prescriptions = prescription.split("\n")
        context = {'email': email, "prescriptions":prescriptions, "doctor": doctor}
        html_message = render_to_string('doctor/mail_message.html',context)
        send_mail("Thank you for using Medicure services!!", "Get Well soon!!", EMAIL_HOST_USER, [email],html_message=html_message,fail_silently=False)
        prescription = "prescription has been sent successfully to "+" "+email
        return render(request,'doctor/prescription_form.html',{'recepient':prescription})

def doctor_logout(request):
    logout(request)
    return redirect("/")

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def dashboard_doctor(request):

    search_term = request.GET.get('term')
    contex = {}
    from doctor.models import DoctorInfo
    doctor=DoctorInfo.objects.filter(user__id=request.user.id).first()
    appointments = AppointmentDetails.objects.filter(Q(create_by_id=doctor.id) | Q(appointment_status=1))
    appointment_ids = []
    for appointment in appointments:
        appointment_ids.append(appointment.id)

    booked_appointments = BookedAppointment.objects.filter(appointment_id_id__in=appointment_ids)

    patient_ids = []
    for booked_appointment in booked_appointments:
        if booked_appointment.booked_by_id not in patient_ids:
            patient_ids.append(booked_appointment.booked_by_id)


    patients = User.objects.filter(id__in=patient_ids)
    print('patientss', patients)

    if search_term == None:
        search_term = ""
    filtered_patients = patients.filter(Q(first_name__icontains=search_term) | Q(last_name__icontains=search_term))
   
    contex = {
        "patients": filtered_patients
    }
    return render(request, 'doctor/dashboard_doctor.html', contex)

# Apoointement Portion for doctor views..........................

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def appointment(request):
    context={}
    from appointment.models import AppointmentDetails
    appointments=AppointmentDetails.objects.filter(create_by=request.user.doctorinfo)
    context={
        'appointments':appointments
    }
    return render(request,'doctor/appointments.html',context)

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def add_appointment(request):
    if request.method=='POST':
        appointment_add_form=AddAppointmentForm(request.POST or None,request.FILES or None)
        if appointment_add_form.is_valid():
            add_appointment=appointment_add_form.save(commit=False)
            add_appointment.create_by=request.user.doctorinfo
            add_appointment.save()
            return redirect('appointment')
        else:
            context={
                'appointment_add_form':appointment_add_form
            }
            return render(request,'doctor/add_appointment.html',context)
    else:
        appointment_add_form=AddAppointmentForm()
        context={
            'appointment_add_form':appointment_add_form
        }
        return render(request,'doctor/add_appointment.html',context)

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def edit_appointment(request,pk):
    try:
        appointment=AppointmentDetails.objects.get(id=pk,create_by=request.user.doctorinfo)
    except:
        return redirect('appointment')
    if request.method=='POST':   
        appointment_edit_form=AddAppointmentForm(request.POST or None,request.FILES,instance=appointment)
        if appointment_edit_form.is_valid():
            update=appointment_edit_form.save(commit=False)
            update.uploaded_by=request.user.doctorinfo
            update.save()
            return redirect('appointment')
        else:
            context={
                'appointment_edit_form':appointment_edit_form,
                'appointment':appointment
            }
            return render(request,'doctor/appointment_edit_form.html',context)
    else:
        appointment_edit_form=AddAppointmentForm(request.POST or None,request.FILES,instance=appointment)
        context={
            'appointment_edit_form':appointment_edit_form,
            'appointment':appointment
        }
        return render(request,'doctor/appointment_edit_form.html',context)

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def delete_appointment(request,pk):
    
    try:
        appointment=AppointmentDetails.objects.get(id=pk,create_by=request.user.doctorinfo)
        appointment.delete()
    except:
      
        return redirect('appointment')
    return redirect('appointment')

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def book_appointment(request):
    appointment=AppointmentDetails.objects.filter(create_by=request.user.doctorinfo)

    ID=[]
    for a in appointment:
        ID.append(a.id)
     
    booked_appointments=BookedAppointment.objects.filter(appointment_id__in=ID)
    context={
        'appointments':booked_appointments
    }
    return render(request,'doctor/booked_appointments.html',context)
    
@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def delete_booked_appointment(request,pk):
    try:
        ap=BookedAppointment.objects.get(id=pk)
      
        # if ap.booked_by==request.user.profile:
        ad=AppointmentDetails.objects.get(id=ap.appointment_id.id)
        if ad.create_by==request.user.doctorinfo:
            ad.appointment_status=0
            ad.save()
            ap.delete()
        else:
            return redirect('book_appointment')        
    except:
        return redirect('book_appointment')
    return redirect('book_appointment')

#For Pnemonia check
@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def showimage(request): 
    form= BlockImageForm(request.POST, request.FILES)


    if form.is_valid():
        form.save()
        lastimage = ImageBlock.objects.latest('id')
        imagefile = lastimage.imageblock
        result = predImageBlock(imagefile)


        if result[0][0] >= 0.5:

            #For pnenumonia prediction

            result=pred1(imagefile)
        
            context={}
            if result[0][0] == 1:
                prediction = 'You are suffering from pneumonia'
                disease_name="Pneumonia"
                # saving  user information who predict pneumonia and suggesting doctors
                predict=WhoPredictDisease(predict_by=request.user.profile,predicted_disease=disease_name)
                predict.save()
                disease=Disease1.objects.filter(name__icontains=disease_name)
                listDoctorID=[]
                for d in disease:
                    listDoctorID.append(d.doctor.id)
                disease_doctor_list=DoctorInfo.objects.filter(Q(id__in=listDoctorID))
                context= {
                'imagefile':imagefile,
                'form': form,
                'sur':prediction,
                'disease_doctor_list':disease_doctor_list,
                }
                return render(request, 'doctor/image.html', context)
            else:
                prediction = "Your health is Normal"
                context= {
                'imagefile':imagefile,
                'form': form,
                'sur':prediction,
                }        
                return render(request, 'doctor/image.html', context)

        else:   
            prediction = "You can not upload this image"
            contex = {'sur': prediction}
            return render(request, 'doctor/image.html', contex)
    if request.method == "GET":
        sur = ' '
        imagefile = ''
        context= {
            'imagefile':imagefile,
            'form': form,
            'sur':sur,
            }
        return render(request, 'doctor/image.html', context)
       
@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def diabetes(request):

    if request.method == "GET":
        diabetes_form=DiabetesForm()
        contex={
            'diabetes_form':diabetes_form
        }
        return render(request,'doctor/diabetes.html', contex)


    elif  request.method=="POST":
        
        diabetes_form=DiabetesForm(request.POST)
        if diabetes_form.is_valid:
            diabetes_form.save()
            from patient.models import Diabetes
            ob = Diabetes.objects.latest('id')

            sur=pred_diabetes(ob)
            
           

            sur=", ".join( repr(e) for e in sur).strip("''")
          
            
            if sur== '1':
                context = {}
                result= "Yes, You are suffering  from Diabetes problems"
                predicted_disease_name="Diabetes"
                predict=WhoPredictDisease(predict_by=request.user.profile,predicted_disease=predicted_disease_name)
                predict.save()
                disease=Disease1.objects.filter(name__icontains=predicted_disease_name)
                listDoctorID=[]
                for d in disease:
                    listDoctorID.append(d.doctor.id)
                disease_doctor_list=DoctorInfo.objects.filter(Q(id__in=listDoctorID))
                
                context={
                    'sur': result,
                    'disease_doctor_list':disease_doctor_list,
                }
                return render(request,'doctor/diabetes_results.html', context)

            elif sur=='0':
                context = {}
                context={'sur':'You are not suffering from diabetes problem',}
                return render(request,'doctor/diabetes_results.html', context)

@login_required(login_url='doctor_login')
@allowed_users(allowed_roles=['DOCTOR'])
def heart(request):
    if request.method=="GET":
        heart_form=HeartForm()
        contex={
            'heart_form':heart_form
        }
        return render(request,'doctor/heart.html', contex)
    if request.method =="POST":
        contex = {}
        if request.POST.get('age'):
            heart = Heart()

            age = request.POST.get('age')
        
            
            sex = request.POST.get('sex')
            sex = sex.lower()
            if sex == 'male':
                sex = 1
            elif sex == 'female':
                sex = 0
            elif sex == 'other':
                sex = 0.5
            
            cp = request.POST.get('cp')
            cp = cp.lower()
            if cp == "typical angina":
                cp = 0
            elif cp == "atypical angina":
                cp = 1
            elif cp == "non-anginal pain":
                cp = 2
            elif cp == 'asymptomatic':
                cp == 3

            
            trestbps = request.POST.get('trestbps')
            
            chol = request.POST.get('chol')
            
            fbs = request.POST.get('fbs')
            fbs = fbs.lower()
            if fbs == 'true':
                fbs = 1
            elif fbs == 'false':
                fbs = 0

            restecg = request.POST.get('restecg')
            restecg = restecg.lower()
            if restecg == "normal":
                restecg = 0
            elif restecg == "having st-t":
                restecg = 1
            elif restecg == 'hypertrophy':
                restecg = 2

            thalach = request.POST.get('thalach')
        

            exang = request.POST.get('exang')
            exang = exang.lower()

            if exang== 'yes':
                exang = 1
            elif exang == 'no':
                exang = 0
            oldpeak = request.POST.get('oldpeak')
            slope = request.POST.get('slope')
            slope = slope.lower()
            if slope =='upsloping':
                slope = 0
            elif slope == 'flat':
                slope = 1
            elif slope=='downsloping':
                slope =2

            ca = request.POST.get('ca')

            thal = request.POST.get('thal')
            thal = thal.lower()

            if thal =="normal":
                thal = 0
            elif thal == 'fixed defect':
                thal = 1
            elif thal =="reversable defect":
                thal = 2


            heart.age = age
            heart.sex = sex
            heart.cp = cp
            heart.chol = chol
            heart.trestbps = trestbps
            heart.fbs = fbs
            heart.restecg = restecg
            heart.thalach = thalach
            heart.exang = exang
            heart.oldpeak = oldpeak
            heart.slope = slope
            heart.ca = ca
            heart.thal = thal
    
            heart.save()

            ob=Heart.objects.latest('id')
            sur=pred_heart(ob)
            sur=", ".join( repr(e) for e in sur).strip("''")
            context={}
            if sur== '1':
                
                name= "Yes, You are suffering from heart problems"
                predicted_disease_name="Heart"
                predict=WhoPredictDisease(predict_by=request.user.profile,predicted_disease=predicted_disease_name)
                predict.save()
                disease=Disease1.objects.filter(name__icontains=predicted_disease_name)
                listDoctorID=[]
                for d in disease:
                    listDoctorID.append(d.doctor.id)
                disease_doctor_list=DoctorInfo.objects.filter(Q(id__in=listDoctorID))
                context={
                    'sur':name,
                    'disease_doctor_list':disease_doctor_list
                }
            elif sur=='0':
                name="You are not suffering from heart problems"
                context={
                    'sur':name,
                }
            
            return render(request,'doctor/heart_results.html', context)
 