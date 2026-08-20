class CyberToast{

    success(message){

        this.show(message,"success");

    }

    error(message){

        this.show(message,"danger");

    }

    info(message){

        this.show(message,"info");

    }

    show(message,type){

        const toast=document.createElement("div");

        toast.className=`cyber-toast ${type}`;

        toast.innerHTML=message;

        document.body.appendChild(toast);

        setTimeout(()=>{
            toast.classList.add("show");
        },50);

        setTimeout(()=>{
            toast.classList.remove("show");
            setTimeout(()=>toast.remove(),300);
        },3500);

    }

}

window.Toast=new CyberToast();