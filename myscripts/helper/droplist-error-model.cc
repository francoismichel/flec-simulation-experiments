#include "droplist-error-model.h"

using namespace std;

NS_OBJECT_ENSURE_REGISTERED(DroplistErrorModel);
 
TypeId DroplistErrorModel::GetTypeId(void) {
    static TypeId tid = TypeId("DroplistErrorModel")
        .SetParent<ErrorModel>()
        .AddConstructor<DroplistErrorModel>()
        ;
    return tid;
}
 
DroplistErrorModel::DroplistErrorModel()
    : packet_num(0) { }

void DroplistErrorModel::DoReset(void) { }
 
bool DroplistErrorModel::DoCorrupt(Ptr<Packet> p) {
    if(drops.find(++packet_num) == drops.end())
        return false;
    cout << "Dropping packet number " << packet_num << endl;
    return true;
}

void DroplistErrorModel::SetDrop(int packet_num) {
    drops.insert(packet_num);
}


void SetDrops(Ptr<DroplistErrorModel> drop_model, string drops_in) {
    char *cstr = new char[drops_in.length()+1];
    strcpy(cstr, drops_in.c_str());
    char *p = strtok(cstr,",");
    while (p) {
        drop_model->SetDrop(stoi(p));
        p = strtok(NULL,",");
    }
    delete[] cstr;
}